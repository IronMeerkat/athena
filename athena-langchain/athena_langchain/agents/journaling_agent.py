from __future__ import annotations

import json
from typing import TypedDict

from langgraph.graph import END, StateGraph
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from athena_langchain.config import Settings
from athena_langchain.registry import PUBLIC_AGENTS as REGISTRY
from athena_langchain.registry.agents_base import (
    AgentConfig,
    AgentEntry,
)


class AgentState(TypedDict):
    user_message: str
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
        chain = prompt | llm
        out = chain.invoke({
            "user_message": state["user_message"],
        })
        # LangChain BaseMessage has .content; fallback to string
        content = getattr(out, "content", None)
        text = (content if isinstance(content, str) else str(out)).strip()
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


