from __future__ import annotations

import json
from typing import TypedDict, Optional, Any, Dict

from langgraph.graph import END, StateGraph
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from athena_langchain.config import Settings
from athena_langchain.registry import SENSITIVE_AGENTS as REGISTRY
from athena_langchain.registry.agents_base import (
    AgentConfig,
    AgentEntry,
)


import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class AgentState(TypedDict, total=False):
    user_message: str
    text: str
    assistant: str


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
        (
            "human",
            "{user_message}",
        ),
    ])

    def converse(state: AgentState) -> AgentState:
        # Normalize DRF-style payloads: accept either "user_message" or "text"
        logger.info(f"state: {state}")
        incoming_text = str(state.get("user_message") or state.get("text") or "").strip()

        if state.get("disconnect"):
            logger.info(f"disconnect: {state.get('disconnect')}")
            # return
            # TODO implement some summary agent/tool here


        # No-op on empty input: return ack by leaving assistant empty
        if not incoming_text:
            state["assistant"] = ""
            return state

        chain = prompt | llm
        out = chain.invoke({
            "user_message": incoming_text,
        })

        logger.info(f"content: {out.content}")
        text = (out.content if isinstance(out.content, str) else str(out)).strip()
        state["assistant"] = text
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


