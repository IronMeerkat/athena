import asyncio
import time
from enum import Enum
from typing import Any, Dict, List, Literal

from athena_celery import shared_task
from athena_logging import get_logger
from athena_settings import settings
from langchain.embeddings import init_embeddings
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import RunnableConfig
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field, field_validator
from typing_extensions import Annotated

from utils.mood_redis import get_current_mood
from prompts import DEFAULT_TELEGRAM_MESSAGES, AI_MESSAGE_1
from integrations.telegram import send_telegram_message
from utils import (BaseState, MsgFieldType, agentless_start, archive_thread,
                   checkpointer, memory, store, vectorstore)
from tools import tools
from utils.memory_engine import get_memory_context_async
from utility_agents import determine_tone, determine_topics
from utility_agents.topic import TopicLiteral

logger = get_logger(__name__)


# Base model (bound per-turn using tone settings)
base_model = ChatOpenAI(model="gpt-5")

class TelegramState(BaseState):
    messages: MsgFieldType = Field(default_factory=lambda: DEFAULT_TELEGRAM_MESSAGES)
    session_id: int
    temperature: float = 0.9
    reasoning_effort: str = "medium"
    verbosity: str = "medium"
    topics: List[TopicLiteral] = Field(default_factory=list)
    needs_restart: bool = False


async def primer(state: TelegramState) -> TelegramState:

    logger.info(f"messages at start: {len(state.messages)}")

    # Get memory context for this query (async, runs in thread pool)
    memory_context = await get_memory_context_async(state.text)

    # Add user message
    state.messages.append(HumanMessage(content=state.text))

    # Add memory context as system message if available
    if memory_context:
        state.messages.append(SystemMessage(content=memory_context))

    # Add mood-based behavioral context
    try:

        mood = get_current_mood(user_id=str(1))
        if mood:
            mood_prompt = generate_mood_system_prompt(mood)
            state.messages.append(SystemMessage(content=mood_prompt))
    except Exception as e:
        logger.debug(f"Failed to add mood context: {e}")

    # Determine tone and other settings
    tone = await determine_tone(state)
    state.temperature = max(0.0, min(2.0, float(tone.temperature)))
    state.reasoning_effort = str(tone.reasoning_effort)
    state.verbosity = str(tone.verbosity)

    # state.topics = (await determine_topics(state)).topics

    # for topic in state.topics:
    #     state.messages.append(TOPIC_PROMPT_DICT[topic])

    return state

async def node_converse(state: TelegramState) -> TelegramState:

    logger.info(f"messages at converse: {len(state.messages)}")

    dynamic_model = base_model.bind(
        temperature=state.temperature,
        reasoning_effort=state.reasoning_effort,
        verbosity=state.verbosity,
    )
    dynamic_agent = create_react_agent(dynamic_model, store=store, state_schema=TelegramState, tools=tools)

    out = await dynamic_agent.ainvoke(state)

    # Memory storage moved to archive_thread for better performance
    # No real-time memory storage - this eliminates embedding calls during conversation

    state.messages = out["messages"]

    logger.info(f"messages at end: {len(state.messages)}")

    # Purge tool messages after tool use to keep context clean for next turn
    logger.info(f"Messages before purging: {len(state.messages)}")

    purged_messages = []
    for msg in state.messages:
        # Keep human, AI (non-tool-only), and system messages
        if msg.type in ("human", "system"):
            purged_messages.append(msg)
        elif msg.type == "ai":
            # Keep AI messages but skip those that only contain tool calls without content
            if not (hasattr(msg, 'tool_calls') and msg.tool_calls and not msg.content.strip()):
                purged_messages.append(msg)
        # Skip tool messages entirely (msg.type == "tool")

    state.messages = purged_messages
    logger.info(f"Messages after purging: {len(state.messages)}")

    return state


graph = StateGraph(TelegramState)
graph.add_node("route", lambda state: state, defer=True)
graph.add_node("primer", primer, defer=True)
graph.add_node("converse", node_converse)
graph.add_node("restart", lambda state: state, defer=True)

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

@shared_task(name="telegram_agent_task", bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 2, 'countdown': 3})
async def telegram_agent_task(self, **kwargs):

    config = RunnableConfig(
        max_concurrency=6,
        configurable={
            "thread_id": str(kwargs['session_id']),
            "checkpoint_ns": "telegram"
        }
    )

    message_sent = False
    try:
        if kwargs['text'] == '/start':
            if await agentless_start(kwargs['session_id'], namespace="telegram"):
                # Reinitialize agent state
                init_state = TelegramState(messages=DEFAULT_TELEGRAM_MESSAGES, text=kwargs['text'], session_id=kwargs['session_id'])
                await telegram_agent.ainvoke(init_state, config=config)
                send_telegram_message(kwargs['session_id'], AI_MESSAGE_1)
                message_sent = True
            else:
                send_telegram_message(kwargs['session_id'], "Sorry, I hit an error. Please try again.")
                message_sent = True
        else:
            result = await telegram_agent.ainvoke(kwargs, config=config)
            send_telegram_message(result['session_id'], result['messages'][-1].content)
            message_sent = True
    except Exception as e:
        logger.exception(f"telegram_agent_task failed on attempt {self.request.retries + 1}: {e}")

        # Only send error message once, don't retry if message was already sent
        if not message_sent and self.request.retries >= 2:
            try:
                send_telegram_message(kwargs['session_id'], "Sorry, I'm experiencing technical difficulties. Please try again later.")
            except:
                logger.exception("Failed to send error message")
        elif not message_sent:
            # Only retry if no message was sent yet
            logger.warning(f"Retrying telegram_agent_task in 3 seconds (attempt {self.request.retries + 1}/2)")
            raise

