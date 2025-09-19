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

from utils import store, checkpointer, vectorstore, tools, BaseState, MsgFieldType, archive_thread
from utility_agents import determine_tone, determine_topics
from utility_agents.topic import TopicLiteral
from agents.prompts import *
from integrations.telegram import send_telegram_message
from athena_logging import get_logger

logger = get_logger(__name__)


# Base model (bound per-turn using tone settings)
base_model = ChatOpenAI(model="gpt-5")

DEFAULT_START_MESSAGES = [SYSTEM_PROMPT_1, AI_PROMPT_1]

class TelegramState(BaseState):
    messages: MsgFieldType = Field(default_factory=lambda: DEFAULT_START_MESSAGES)
    session_id: int
    temperature: float = 0.9
    reasoning_effort: str = "medium"
    verbosity: str = "medium"
    topics: List[TopicLiteral] = Field(default_factory=list)
    needs_restart: bool = False


async def route(state: TelegramState) -> TelegramState:

    state.topics = []

    if len(state.messages) < len(DEFAULT_START_MESSAGES):
        state.messages = DEFAULT_START_MESSAGES


    if state.needs_restart:
        await checkpointer.adelete_thread(str(state.session_id))
        state.messages = DEFAULT_START_MESSAGES
        state.needs_restart = False


    return state

async def primer(state: TelegramState) -> TelegramState:

    state.messages.append(HumanMessage(content=state.text))
    tone = await determine_tone(state)
    state.temperature = max(0.0, min(2.0, float(tone.temperature)))
    state.reasoning_effort = str(tone.reasoning_effort)
    state.verbosity = str(tone.verbosity)

    state.topics = (await determine_topics(state)).topics

    for topic in state.topics:
        state.messages.append(TOPIC_PROMPT_DICT[topic])


    return state

async def node_converse(state: TelegramState) -> TelegramState:


    dynamic_model = base_model.bind(
        temperature=state.temperature,
        reasoning_effort=state.reasoning_effort,
        verbosity=state.verbosity,
    )
    dynamic_agent = create_react_agent(dynamic_model, store=store, state_schema=TelegramState, tools=tools)

    out = await dynamic_agent.ainvoke(state)

    state.messages = out["messages"]

    return state

async def node_restart(state: TelegramState) -> TelegramState:

    await archive_thread(state, namespace="telegram")
    state.needs_restart = True
    state.messages = DEFAULT_START_MESSAGES
    return state



graph = StateGraph(TelegramState)
graph.add_node("route", route)
graph.add_node("primer", primer, defer=True)
graph.add_node("converse", node_converse)
graph.add_node("restart", node_restart)

graph.set_entry_point("route")
graph.add_conditional_edges(
    "route",
    lambda s: s.text.strip() == "/start",
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
            "thread_id": str(kwargs['session_id']),
            "checkpoint_ns": "telegram"
        }
    )
    try:

        if kwargs['text'] == '/start':
            result = await telegram_agent.ainvoke(kwargs, config=config)
            await checkpointer.adelete_thread(str(kwargs['session_id']))
            result = await telegram_agent.ainvoke(kwargs, config=config) # neccessary cuz of a langchain bug
            send_telegram_message(result['session_id'], result['messages'][-1].content)
        else:
            result = await telegram_agent.ainvoke(kwargs, config=config)
            send_telegram_message(result['session_id'], result['messages'][-1].content)
    except Exception as e:
        logger.exception("telegram_agent_task failed")
        send_telegram_message(kwargs['session_id'], "Sorry, I hit an error. Please try again.")

