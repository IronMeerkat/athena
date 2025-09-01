from __future__ import annotations

import json
from typing import TypedDict, Optional, Any, Dict, List

from langgraph.graph import END, StateGraph
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from athena_langchain.config import Settings
from athena_langchain.registry import SENSITIVE_AGENTS as REGISTRY
from athena_langchain.registry.agents_base import (
    AgentConfig,
    AgentEntry,
)
from athena_langchain.memory.chat_history import get_session_history_factory


import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class AgentState(TypedDict, total=False):
    user_message: str
    text: str
    assistant: str
    connect: bool
    disconnect: bool
    convo_history: List[Dict[str, str]]
    session_id: str


def build_graph(settings: Settings, llm: BaseChatModel) -> StateGraph:
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            (
                "You are Athena, the goddess of wisdom, strategy, and science, "
                "and you are a warm, concise journaling companion. "
                "Respond with a short empathetic reflection and a follow-up question. "
                "Do not include lists or markdown. Output ONLY plain text."
            ),
        ),
        MessagesPlaceholder(variable_name="history"),
        (
            "human",
            "{user_message}",
        ),
    ])

    def converse(state: AgentState) -> AgentState:
        # Normalize DRF-style payloads: accept either "user_message" or "text"
        logger.info(f"state: {state}")
        incoming_text = str(state.get("user_message") or state.get("text") or "").strip()
        session_id = str(state.get("session_id") or "").strip()
        history_factory = get_session_history_factory(settings)
        redis_history = history_factory(session_id) if session_id else None

        def to_lc_messages(items: List[Dict[str, str]]) -> List[BaseMessage]:
            messages: List[BaseMessage] = []
            for item in items:
                role = (item.get("role") or "").lower()
                content = item.get("content") or item.get("text") or ""
                if not content:
                    continue
                if role == "assistant":
                    messages.append(AIMessage(content=content))
                else:
                    messages.append(HumanMessage(content=content))
            return messages

        if state.get("connect"):
            convo_history = state.get("convo_history") or []
            logger.info(f"connect: {state.get('connect')}")
            # Load the chat history into redis on connect
            try:
                if redis_history is not None:
                    # Reset and load prior messages
                    # RedisChatMessageHistory doesn't have a clear() method; we just append.
                    for item in convo_history:
                        role = (item.get("role") or "").lower()
                        content = item.get("content") or item.get("text") or ""
                        if not content:
                            continue
                        if role == "assistant":
                            redis_history.add_ai_message(content)
                        else:
                            redis_history.add_user_message(content)
            except Exception:
                pass

            # If chat is new, send the first message
            if not convo_history:
                first = (
                    "Hi, I'm Athena. What's on your mind today?"
                )
                try:
                    if redis_history is not None:
                        redis_history.add_ai_message(first)
                except Exception:
                    pass
                state["assistant"] = first
                return state

        if state.get("disconnect"):
            logger.info(f"disconnect: {state.get('disconnect')}")
            # Send the full history back (for DRF to persist/confirm)
            try:
                if redis_history is not None:
                    hist_items: List[Dict[str, str]] = []
                    for m in redis_history.messages:
                        role = "assistant" if isinstance(m, AIMessage) else "user"
                        hist_items.append({"role": role, "content": str(m.content)})
                    state["history_snapshot"] = {"messages": hist_items}
            except Exception:
                pass
            state["assistant"] = ""
            return state


        # No-op on empty input: return ack by leaving assistant empty
        if not incoming_text:
            state["assistant"] = ""
            return state

        # Build LC history for context
        lc_history: List[BaseMessage] = []
        try:
            if redis_history is not None:
                # Append incoming user message prior to generation to keep consistent history
                redis_history.add_user_message(incoming_text)
                lc_history = list(redis_history.messages)
        except Exception:
            lc_history = to_lc_messages(state.get("convo_history") or [])

        chain = prompt | llm
        out = chain.invoke({
            "user_message": incoming_text,
            "history": lc_history,
        })

        logger.info(f"content: {out.content}")
        text = (out.content if isinstance(out.content, str) else str(out)).strip()
        state["assistant"] = text
        try:
            if redis_history is not None and text:
                redis_history.add_ai_message(text)
        except Exception:
            pass
        return state

    graph = StateGraph(AgentState)
    graph.add_node("converse", converse)
    graph.set_entry_point("converse")
    graph.add_edge("converse", END)
    return graph


REGISTRY.register(
    "journaling",
    AgentEntry(
        config=AgentConfig(
            name="Journaling",
            description=(
                "A lightweight, ephemeral journaling companion that reflects and asks questions."
            ),
            model_name="gpt-5-mini",
            temperature=0.8,
        ),
        build_graph=build_graph,
    ),
)


