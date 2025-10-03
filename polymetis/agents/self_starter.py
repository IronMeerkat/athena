import asyncio

import time
from typing_extensions import Annotated

from athena_settings import settings
from typing import Dict, List, Any
from langgraph.graph.state import RunnableConfig
from pydantic import BaseModel, Field
from athena_celery import shared_task

from langchain.embeddings import init_embeddings
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph import END, StateGraph, START
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from prompts import SUPER_SYSTEM_PROMPT
from utils import store, checkpointer, vectorstore, BaseState, MsgFieldType
from tools import tools
from integrations.telegram import send_telegram_message
from athena_logging import get_logger

logger = get_logger(__name__)


class TelegramState(BaseState):
    remaining_steps: int = 5
    messages: MsgFieldType = Field(default_factory=lambda: SUPER_SYSTEM_PROMPT) # PLACEHOLDER FOR STARTER PROMPT
    telegram_chat_id: int = settings.TELEGRAM_CHAT_ID
    temperature: float = 0.9
    reasoning_effort: str = "low"
    verbosity: str = "low"

base_model = ChatOpenAI(model="gpt-5-mini",
                        temperature=0.9,
                        reasoning_effort="low",
                        verbosity="low")

agent = create_react_agent(base_model, state_schema=TelegramState, store=store, tools=tools)

async def converse(state: TelegramState) -> TelegramState:
    return await agent.ainvoke(state)


graph = StateGraph(TelegramState)
graph.add_node("converse", converse)
graph.set_entry_point("converse")
graph.add_edge(START, "converse")
graph.add_edge("converse", END)

self_starter_agent = graph.compile(checkpointer=checkpointer).with_config(
    {"configurable": {"checkpoint_ns": "self_starter"}}
)

@shared_task(name="self_starter_agent_task")
async def self_starter_agent_task(**kwargs):
    config = RunnableConfig(
        max_concurrency=6,
        configurable={
            "checkpoint_ns": "self_starter",
            "telegram_chat_id": settings.TELEGRAM_CHAT_ID
        }
    )
    result = await self_starter_agent.ainvoke(kwargs, config=config)
    send_telegram_message(settings.TELEGRAM_CHAT_ID, result['messages'][-1].content)
    return result