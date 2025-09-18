import asyncio

import time
from typing_extensions import Annotated
from enum import Enum

from athena_settings import settings
from typing import Dict, List, Any, Literal
from langgraph.graph.state import RunnableConfig
from pydantic import BaseModel, Field, field_validator
from athena_celery import shared_task

from langchain.embeddings import init_embeddings
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph import END, StateGraph, START
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from utils import store, checkpointer, vectorstore, tools, BaseState, MsgFieldType
from utility_agents import determine_tone, determine_topics
from utility_agents.topic import TopicLiteral
from agents.prompts import *
from integrations.telegram import send_telegram_message
from athena_logging import get_logger

logger = get_logger(__name__)


# Base model (bound per-turn using tone settings)
base_model = ChatOpenAI(model="gpt-5")

class TelegramState(BaseState):
    messages: MsgFieldType = Field(default_factory=lambda: [SYSTEM_PROMPT_1, AI_PROMPT_1])
    telegram_chat_id: int
    temperature: float = 0.9
    reasoning_effort: str = "medium"
    verbosity: str = "medium"
    topics: List[TopicLiteral] = Field(default_factory=list)


async def primer(state: TelegramState) -> TelegramState:

    state.messages.append(HumanMessage(content=state.text))

    tone = await determine_tone(state)
    state.temperature = max(0.0, min(2.0, float(tone.temperature)))
    state.reasoning_effort = str(tone.reasoning_effort)
    state.verbosity = str(tone.verbosity)

    state.topics = await determine_topics(state)

    for topic in state.topics:
        state.messages.append(TOPIC_PROMPT_DICT[topic])

    logger.info(f"state.messages: {len(state.messages)}")

    return state

async def node_converse(state: TelegramState) -> TelegramState:


    dynamic_model = base_model.bind(
        temperature=state.temperature,
        reasoning_effort=state.reasoning_effort,
        verbosity=state.verbosity,
    )
    dynamic_agent = create_react_agent(dynamic_model, state_schema=TelegramState, store=store, tools=tools)

    out = await dynamic_agent.ainvoke(state)


    state.messages = out["messages"]


    return state

async def node_restart(state: TelegramState) -> TelegramState:

    try:
        session_id = f"telegram:{state.telegram_chat_id}"
        texts = []
        metadatas = []
        for idx, msg in enumerate(state.interesting_messages):
            timestamp_ms = int(time.time() * 1000)
            if msg.content == '/start':
                continue
            texts.append(msg.content)
            if len(msg.content) > 140:
                await store.aput(
                    namespace="global",
                    key=f"telegram:{state.telegram_chat_id}:{timestamp_ms}:{idx}",
                    value={
                    "text": msg.content,
                    "agent": "telegram",
                    "role": msg.type,
                    "session_id": session_id,
                    "chat_id": state.telegram_chat_id,
                    "ts": timestamp_ms,
                })
            metadatas.append({
                "agent": "telegram",
                "role": msg.type,
                "session_id": session_id,
                "chat_id": state.telegram_chat_id,
                "ts": timestamp_ms,
            })
        vectorstore.add_texts(texts, metadatas=metadatas)
        await checkpointer.adelete_thread(str(state.telegram_chat_id))
        await checkpointer._redis.flushall(asynchronous=True)
        await checkpointer.asetup()
        # checkpointer.delete_thread(str(state.telegram_chat_id))
    except Exception:
        logger.exception("delete thread failed")
    return TelegramState(
        # text=AI_PROMPT_1.content,
        text="",
        telegram_chat_id=state.telegram_chat_id,
        # messages=[SYSTEM_PROMPT_1, AI_PROMPT_1]
    )


graph = StateGraph(TelegramState)
graph.add_node("route", lambda x: x)
graph.add_node("primer", primer)
graph.add_node("converse", node_converse, defer=True)  # good hygiene if branches ever differ
graph.add_node("restart", node_restart)

graph.set_entry_point("route")
graph.add_conditional_edges(
    "route",
    lambda s: s.text == "/start",
    {True: "restart", False: "primer"},
)


graph.add_edge("primer", "converse")
graph.add_edge("converse", END)
graph.add_edge("restart", END)


telegram_agent = graph.compile(checkpointer=checkpointer).with_config(
    {"configurable": {"checkpoint_ns": "telegram"}}
)

# https://platform.openai.com/chat/edit?models=gpt-5&optimize=true
# https://platform.openai.com/docs/guides/tools-connectors-mcp?quickstart-panels=remote-mcp

@shared_task(name="telegram_agent_task")
async def telegram_agent_task(**kwargs):

    config = RunnableConfig(
        max_concurrency=6,
        configurable={
            "thread_id": str(kwargs['telegram_chat_id']),
            "checkpoint_ns": "telegram"
        }
    )
    try:
        result = await telegram_agent.ainvoke(kwargs, config=config)
        send_telegram_message(result['telegram_chat_id'], result['messages'][-1].content)
    except Exception as e:
        logger.exception("telegram_agent_task failed")
        send_telegram_message(kwargs['telegram_chat_id'], "Sorry, I hit an error. Please try again.")

