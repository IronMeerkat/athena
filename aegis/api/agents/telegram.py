import os
import re
import time
from typing_extensions import Annotated

from langgraph.graph.message import add_messages
from django.conf import settings
from typing import Dict, List, Any
from langgraph.graph.state import RunnableConfig
from pydantic import BaseModel, Field, computed_field
from celery import shared_task

from langchain.embeddings import init_embeddings
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.redis import RedisSaver
from langgraph.store.postgres import PostgresStore
from langgraph.graph import END, StateGraph
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_postgres import PGVectorStore, PGEngine
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from api.agents.utils import store, checkpointer, vectorstore, tools, BaseState, MsgFieldType

from api.integrations.telegram import send_telegram_message
from athena_logging import get_logger

logger = get_logger(__name__)


SYSTEM_PROMPT_1 = SystemMessage(content=(
    "You are Athena, the goddess of wisdom, strategy, and science, "
    "moonlighting as a helpful assistant on Telegram."
))

SYSTEM_PROMPT_2 = SystemMessage(content=(
    "Decide on the appropriate values for the generation controls."
    " Return ONLY valid JSON for keys: temperature (0-2 float),"
    " reasoning_effort (minimal|medium|heavy), verbosity (low|default|high)."))

AI_PROMPT_1 = AIMessage(content=(
    "Hello! I'm Athena, whats on your mind today?"
))

tone_prompt = ChatPromptTemplate.from_messages([
    SYSTEM_PROMPT_1,
    SystemMessage(content="Decide on the appropriate values for the generation controls. Return ONLY valid JSON for keys: temperature (0-2 float), reasoning_effort (minimal|medium|heavy), verbosity (low|default|high)."),
    HumanMessage(content="{user_message}"),
])

# Base model (bound per-turn using tone settings)
base_model = ChatOpenAI(model="gpt-5")

tone_model = ChatOpenAI(model="gpt-5-nano", temperature=0.1, reasoning_effort="low", verbosity="low")

class ToneSettings(BaseModel):
    temperature: float
    reasoning_effort: str
    verbosity: str


class TelegramState(BaseState):
    remaining_steps: int = 3
    messages: MsgFieldType = Field(default_factory=lambda: [SYSTEM_PROMPT_1, AI_PROMPT_1])
    telegram_chat_id: int
    temperature: float = 0.9
    reasoning_effort: str = "medium"
    verbosity: str = "medium"

tone_chain = tone_prompt | tone_model.with_structured_output(ToneSettings)

def analyze_tone(state: TelegramState) -> TelegramState:

    if state.text == "/start":
        return state

    tone = tone_chain.invoke({"user_message": state.text})

    state.temperature = max(0.0, min(2.0, float(tone.temperature)))
    state.reasoning_effort = str(tone.reasoning_effort)
    state.verbosity = str(tone.verbosity)

    return state

def node_converse(state: TelegramState) -> TelegramState:

    if state.text == '/start':
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

                    store.put(
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

            checkpointer.delete_thread(str(state.telegram_chat_id))
        except Exception:
            logger.exception("delete thread failed")

        return TelegramState(
            text=state.text,
            telegram_chat_id=state.telegram_chat_id,
        )

    state.messages.append(HumanMessage(content=state.text))

    dynamic_model = base_model.bind(
        temperature=state.temperature,
        reasoning_effort=state.reasoning_effort,
        verbosity=state.verbosity,
    )
    dynamic_agent = create_react_agent(dynamic_model, state_schema=TelegramState, store=store, tools=tools)

    out = dynamic_agent.invoke(state)
    logger.info(f"Conversing with messages:")
    for msg in state.messages:
        logger.info(f"  {msg.type}: {msg.content}")


    state.messages = out["messages"]


    return state

graph = StateGraph(TelegramState)
graph.add_node("tone", analyze_tone)
graph.add_node("converse", node_converse)
graph.set_entry_point("tone")
graph.add_edge("tone", "converse")
graph.add_edge("converse", END)

telegram_agent = graph.compile(checkpointer=checkpointer).with_config(
    {"configurable": {"checkpoint_ns": "telegram"}}
)

# https://platform.openai.com/chat/edit?models=gpt-5&optimize=true
# https://platform.openai.com/docs/guides/tools-connectors-mcp?quickstart-panels=remote-mcp

@shared_task(name="telegram_agent_task")
def telegram_agent_task(**kwargs):


    config = RunnableConfig(
        configurable={
            "thread_id": str(kwargs['telegram_chat_id']),
            "checkpoint_ns": "telegram"
        }
    )
    try:
        result = telegram_agent.invoke(kwargs, config=config)
        send_telegram_message(result['telegram_chat_id'], result['messages'][-1].content)
    except Exception as e:
        logger.exception("telegram_agent_task failed")
        send_telegram_message(kwargs['telegram_chat_id'], "Sorry, I hit an error. Please try again.")
