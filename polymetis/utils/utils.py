import asyncio
import os
import re
import atexit
import sys
from urllib.parse import quote
import operator

from athena_settings import settings
from typing import Dict, List, Any
from langchain_core.vectorstores import VectorStoreRetriever
from pydantic import BaseModel, Field
from athena_celery import shared_task
from athena_logging import get_logger
from langchain.embeddings import init_embeddings
from langchain_core.embeddings import Embeddings
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.redis import AsyncRedisSaver
from langgraph.store.postgres import PostgresStore
from langgraph.graph import END, StateGraph
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_postgres import PGVectorStore, PGEngine, PGVector
from langchain_postgres.v2.indexes import DistanceStrategy, HNSWIndex
from langchain.tools.retriever import create_retriever_tool
from pydantic import BaseModel as PydanticBaseModel, Field, computed_field
from typing_extensions import Annotated

from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_cohere import CohereRerank
import requests

from utils.build_retriever import build_retriever

# Module logger
logger = get_logger(__name__)

async def get_client_and_tools():

    client = MultiServerMCPClient(
        {
            "ergane": {
                "command": "python",
                "args": ["/app/chalkeion/server.py"],
                "transport": "stdio",
            },

            # "notion": {
            #     "url": "https://mcp.notion.com/mcp",
            #     "transport": "streamable_http",
            #     "headers": get_mcp_headers(),
            # },
        }
    )
    checkpointer : AsyncRedisSaver = AsyncRedisSaver(redis_url=f'redis://{settings.REDIS_URL}')
    await checkpointer.asetup()
    # tools = await client.get_tools()
    tools = []
    return client, tools, checkpointer

vec_options = quote('-c search_path=rag,public', safe='')
vec_dsn = f"{settings.DATABASE_URL}{'&' if '?' in settings.DATABASE_URL else '?'}options={vec_options}"
_db_url_no_driver = re.sub(r'^postgresql\+[^:]+', 'postgresql', settings.DATABASE_URL)
store_options = quote('-c search_path=graph,public', safe='')
store_dsn = f"{_db_url_no_driver}{'&' if '?' in _db_url_no_driver else '?'}options={store_options}"

pg_engine = PGEngine.from_connection_string(vec_dsn)

# Default rag tool placeholder for loader
rag_tool = None


client, tools, checkpointer = asyncio.run(get_client_and_tools())

embeddings = init_embeddings(model="openai:text-embedding-3-small")

vectorstore : PGVectorStore = PGVectorStore.create_sync(
    engine=pg_engine,
    embedding_service=embeddings,
    table_name="docs",
    schema_name="rag",
    distance_strategy=DistanceStrategy.EUCLIDEAN,  # L2
)

index : HNSWIndex = HNSWIndex(distance_strategy=DistanceStrategy.EUCLIDEAN, m=16, ef_construction=64)


_store_cm = PostgresStore.from_conn_string(
store_dsn,
index={"dims": 1536, "embed": embeddings, "fields": ["text"]},
)
store : PostgresStore = _store_cm.__enter__()
atexit.register(lambda: _store_cm.__exit__(None, None, None))


retriever : VectorStoreRetriever | ContextualCompressionRetriever = build_retriever(vectorstore)
rag_tool = create_retriever_tool(
    retriever,
    name="search_docs",
    description="Retrieve and rerank relevant context from the RAG vector store.",
)
tools.append(rag_tool)

MsgFieldType = Annotated[List[BaseMessage], add_messages]

class BaseState(PydanticBaseModel, frozen=False):
    messages: MsgFieldType
    text: str
    remaining_steps: int = 6
    juice: int = 6
    scratch: Annotated[List[str], operator.add] = Field(default_factory=list)
    done: bool = False

    @computed_field
    @property
    def user_message(self) -> HumanMessage:
        for message in self.messages[::-1]:
            if message.type == "human":
                return message
        return HumanMessage(content="")


    @computed_field
    @property
    def assistant_message(self) -> AIMessage:
        for message in self.messages[::-1]:
            if message.type == "ai":
                return message
        return AIMessage(content="")

    @computed_field
    @property
    def interesting_messages(self) -> List[BaseMessage]:
        return [msg for msg in self.messages
                if msg.type in ("human", "ai") and msg.content
                and not msg.additional_kwargs.get("skip_storage", False)]

class BaseUtilityState(BaseState):

    @classmethod
    def from_other_state(cls, other_state: BaseState) -> 'BaseUtilityState':
        self = cls(**other_state.model_dump(exclude={"messages"}))
        self.messages.append(other_state.user_message)
        return self