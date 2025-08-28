from __future__ import annotations

import json
from typing import List, TypedDict

from langgraph.graph import END, StateGraph
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from athena_langchain.config import Settings
from athena_langchain.agents.registry import (
    REGISTRY,
    AgentConfig,
    AgentEntry,
)
from athena_langchain.tools.policies.schedule import save_schedule
from athena_langchain.memory.chat_history import get_session_history_factory


class AgentState(TypedDict):
    session_id: str
    user_message: str
    assistant: str
    schedule: List[dict]


def build_graph(settings: Settings, llm: BaseChatModel) -> StateGraph:
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            (
                "You are Athena, a compassionate productivity coach. "
                "Use the prior conversation in History to respond. "
                "Work with the user on goals and plan a weekly schedule. "
                "Output ONLY JSON with keys 'assistant' and 'schedule' "
                "(list). "
                "Each item: "
                "{start_minutes:int,end_minutes:int,days:[0..6],"
                "goal?:string,strictness:int}. "
                "Strictness (1..10) influences enforcement only; "
                "not goal selection."
            ),
        ),
        (
            "system",
            "History:\n{history}",
        ),
        (
            "human",
            "{user_message}",
        ),
    ])

    def converse(state: AgentState) -> AgentState:
        chain = prompt | llm
        # Pull short chat history for memory
        session_id = state.get("session_id") or "default"
        hist_factory = get_session_history_factory(settings)
        history = hist_factory(session_id)
        hist_msgs = history.messages[-10:]
        history_str = "\n".join(
            [f"{m.type}: {getattr(m, 'content', '')}" for m in hist_msgs]
        )
        out = chain.invoke({
            "history": history_str,
            "user_message": state["user_message"],
        })
        raw = (out.content or "").strip()  # type: ignore[attr-defined]
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"assistant": raw, "schedule": []}
        state["assistant"] = str(data.get("assistant", ""))
        schedule = data.get("schedule") or []
        if isinstance(schedule, list):
            state["schedule"] = schedule
        else:
            state["schedule"] = []
        # Persist schedule
        sid = state.get("session_id") or "default"
        save_schedule(settings, state["schedule"], session_id=sid)
        # Append to chat history
        try:
            # type: ignore[arg-type]
            history.add_user_message(state["user_message"])
            # type: ignore[arg-type]
            history.add_ai_message(state["assistant"])
        except Exception:  # noqa: BLE001 - best-effort history persistence
            # Ignore connectivity errors when writing history
            pass
        return state

    graph = StateGraph(AgentState)
    graph.add_node("converse", converse)
    graph.set_entry_point("converse")
    graph.add_edge("converse", END)
    return graph


REGISTRY.register(
    "goals_scheduler",
    AgentEntry(
        config=AgentConfig(
            name="Goals & Scheduler",
            description=(
                "Discuss goals, update memories, create schedule with per-"
                "block strictness (1-10)."
            ),
            model_name='gpt-5',
        ),
        build_graph=build_graph,
    ),
)
