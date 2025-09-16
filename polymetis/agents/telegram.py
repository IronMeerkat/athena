import asyncio
import nest_asyncio

nest_asyncio.apply()

import time
from typing_extensions import Annotated
from enum import Enum

from django.conf import settings
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
from prompts import *
from integrations.telegram import send_telegram_message
from athena_logging import get_logger

logger = get_logger(__name__)



# Base model (bound per-turn using tone settings)
base_model = ChatOpenAI(model="gpt-5")

lite_model = ChatOpenAI(model="gpt-5-mini", temperature=0.4, reasoning_effort="low", verbosity="low")

class ToneSettings(BaseModel):
    temperature: float
    reasoning_effort: str
    verbosity: str

# Create a Literal type from TOPIC_PROMPT_DICT keys for strict validation
TopicLiteral = Literal["philosophy", "political", "foreign_policy", "science"]

class TopicSettings(BaseModel):
    topics: List[TopicLiteral] = Field(
        description="List of topic keys from TOPIC_PROMPT_DICT",
        min_items=0,
        max_items=len(TOPIC_PROMPT_DICT)
    )

    @field_validator('topics', mode='before')
    @classmethod
    def validate_topics(cls, v):
        """Validate that all topics are valid keys from TOPIC_PROMPT_DICT"""
        if not isinstance(v, list):
            raise ValueError("topics must be a list")

        valid_keys = set(TOPIC_PROMPT_DICT.keys())
        for topic in v:
            if topic not in valid_keys:
                raise ValueError(f"Invalid topic '{topic}'. Must be one of: {', '.join(valid_keys)}")

        return v

class TelegramState(BaseState):
    remaining_steps: int = 5
    messages: MsgFieldType = Field(default_factory=lambda: [SYSTEM_PROMPT_1, AI_PROMPT_1])
    telegram_chat_id: int
    temperature: float = 0.9
    reasoning_effort: str = "medium"
    verbosity: str = "medium"


tone_chain = tone_prompt_template | lite_model.with_structured_output(ToneSettings)
topic_chain = topic_picker_prompt_template | lite_model.with_structured_output(TopicSettings)

def collapse_system_messages(msgs):
    sys_parts, other = [], []
    for m in msgs:
        if isinstance(m, SystemMessage):
            sys_parts.append(m.content)
        else:
            other.append(m)
    # Last-wins is risky; better to concatenate with clear sections.
    combined = "\n\n".join(sys_parts)
    return [SystemMessage(content=combined)] + other

async def primer(state: TelegramState) -> TelegramState:

    tone = await tone_chain.ainvoke({"user_message": state.text})

    try:
        topics = await topic_chain.ainvoke({
            "user_message": state.text,
            "topics": ", ".join(TOPIC_PROMPT_DICT.keys()),
        })

        # Validate the topics output
        if not hasattr(topics, 'topics') or not isinstance(topics.topics, list):
            logger.error(f"Invalid topics output: {topics}")
            topics = TopicSettings(topics=[])  # Default to empty list

        logger.info(f"topics: {topics}")

        # Add topic-specific prompts to messages
        for topic in topics.topics:
            if topic in TOPIC_PROMPT_DICT:
                state.messages.append(TOPIC_PROMPT_DICT[topic])
            else:
                logger.warning(f"Unknown topic '{topic}' not found in TOPIC_PROMPT_DICT")

    except Exception as e:
        logger.exception(f"Error in topic_chain: {e}")
        # Fallback to empty topics list
        topics = TopicSettings(topics=[])

    state.temperature = max(0.0, min(2.0, float(tone.temperature)))
    state.reasoning_effort = str(tone.reasoning_effort)
    state.verbosity = str(tone.verbosity)

    logger.info(f"state.messages: {len(state.messages)}")



async def node_converse(state: TelegramState) -> TelegramState:

    # state.messages = collapse_system_messages(state.messages)

    state.messages.append(HumanMessage(content=state.text))

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
        text=AI_PROMPT_1.content,
        telegram_chat_id=state.telegram_chat_id,
        messages=[SYSTEM_PROMPT_1, AI_PROMPT_1]
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

