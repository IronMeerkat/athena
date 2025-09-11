import os
import re
import logging
import atexit
import sys
from urllib.parse import quote

from django.conf import settings
from typing import Dict, List, Any
from pydantic import BaseModel, Field
from celery import shared_task

from langchain.embeddings import init_embeddings
from langchain_core.embeddings import Embeddings
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.redis import RedisSaver
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
import torch



# Module logger
logger = logging.getLogger(__name__)
# client = MultiServerMCPClient(
#     {
#         "polymetis": {
#             "command": "python",
#             "args": ["/path/to/polymetis_server.py"],
#             "transport": "stdio",
#         },
#     }
# )

tools = []
# tools = client.list_tools()


vec_options = quote('-c search_path=rag,public', safe='')
vec_dsn = f"{settings.DATABASE_URL}{'&' if '?' in settings.DATABASE_URL else '?'}options={vec_options}"
_db_url_no_driver = re.sub(r'^postgresql\+[^:]+', 'postgresql', settings.DATABASE_URL)
store_options = quote('-c search_path=graph,public', safe='')
store_dsn = f"{_db_url_no_driver}{'&' if '?' in _db_url_no_driver else '?'}options={store_options}"

pg_engine = PGEngine.from_connection_string(vec_dsn)

if not any(cmd in sys.argv for cmd in ("migrate", "makemigrations", "collectstatic")):

    embeddings = init_embeddings(model="openai:text-embedding-3-small")

    vectorstore = PGVectorStore.create_sync(
        engine=pg_engine,
        embedding_service=embeddings,
        table_name="docs",
        schema_name="rag",
        distance_strategy=DistanceStrategy.EUCLIDEAN,  # L2
    )

    index = HNSWIndex(distance_strategy=DistanceStrategy.EUCLIDEAN, m=16, ef_construction=64)

    checkpointer = RedisSaver(redis_url=f'redis://{settings.REDIS_URL}/1')

    _store_cm = PostgresStore.from_conn_string(
    store_dsn,
    index={"dims": 1536, "embed": embeddings, "fields": ["text"]},
    )
    store = _store_cm.__enter__()
    atexit.register(lambda: _store_cm.__exit__(None, None, None))


    def _build_retriever() -> Any:
        search_type = os.getenv("RETRIEVAL_SEARCH_TYPE", "mmr")
        k = int(os.getenv("RETRIEVAL_K", "48"))
        fetch_k = int(os.getenv("RETRIEVAL_FETCH_K", "96"))
        lambda_mult = float(os.getenv("RETRIEVAL_MMR_LAMBDA", "0.25"))

        base_kwargs = {"k": k}
        if search_type == "mmr":
            base_kwargs.update({"fetch_k": fetch_k, "lambda_mult": lambda_mult})

        base = vectorstore.as_retriever(search_type=search_type, search_kwargs=base_kwargs)

        if os.getenv("DISABLE_RERANKING", "0") == "1":
            return base

        provider = os.getenv("RERANKER_PROVIDER", "hf").lower()

        # Cohere path (good for prod)
        if provider == "cohere" and CohereRerank is not None and os.getenv("COHERE_API_KEY"):
            try:
                top_n = int(os.getenv("RERANKER_TOPN", "8"))
                model = os.getenv("COHERE_RERANK_MODEL", "rerank-3.5")
                reranker = CohereRerank(model=model, top_n=top_n)
                return ContextualCompressionRetriever(
                    base_retriever=base,
                    base_compressor=reranker,
                )
            except Exception:
                logger.exception("Cohere reranker init failed; falling back to base retriever")
                return base

        # Local HF cross-encoder path (good for RTX 4070 dev)
        if provider == "hf" and HuggingFaceCrossEncoder is not None:
            try:
                model_name = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-large")
                top_n = int(os.getenv("RERANKER_TOPN", "8"))
                try:
                      # type: ignore
                    device_env = os.getenv("RERANKER_DEVICE", "cuda")
                    device = "cuda" if device_env != "cpu" and torch.cuda.is_available() else "cpu"
                except Exception:
                    device = "cpu"

                ce = HuggingFaceCrossEncoder(model_name=model_name, device=device)
                reranker = CrossEncoderReranker(model=ce, top_n=top_n)
                return ContextualCompressionRetriever(
                    base_retriever=base,
                    base_compressor=reranker,
                )
            except Exception:
                logger.exception("HF cross-encoder reranker init failed; falling back to base retriever")
                return base

        return base

    retriever = _build_retriever()
    rag_tool = create_retriever_tool(
        retriever,
        name="search_docs",
        description="Retrieve and rerank relevant context from the RAG vector store.",
    )

    tools.append(rag_tool)
else:
    embeddings : Embeddings = None
    vectorstore : PGVectorStore = None
    index : HNSWIndex = None
    checkpointer = None
    store : PostgresStore = None

MsgFieldType = Annotated[List[BaseMessage], add_messages]

class BaseState(PydanticBaseModel, frozen=False):
    text: str
    remaining_steps: int = 5

    @computed_field
    @property
    def user_message(self) -> str:
        for message in self.messages[::-1]:
            if message.type == "human":
                return message.content
        return ""


    @computed_field
    @property
    def assistant(self) -> str:
        for message in self.messages[::-1]:
            if message.type == "ai":
                return message.content
        return ""

    @computed_field
    @property
    def interesting_messages(self) -> List[BaseMessage]:
        return [msg for msg in self.messages if msg.type in ("human", "ai") and msg.content]