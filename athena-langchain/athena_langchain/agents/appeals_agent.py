from __future__ import annotations
import json
from typing import TypedDict
from langgraph.graph import END, StateGraph
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from athena_langchain.config import Settings
from athena_langchain.agents.registry import REGISTRY, AgentConfig, AgentEntry
from athena_langchain.tools.policies.schedule import (
    get_current_strictness,
    get_current_goal,
)


class AppealState(TypedDict, total=False):
    session_id: str
    # App/site context
    url: str
    title: str
    host: str
    path: str
    package: str
    activity: str
    # User appeal content
    user_justification: str
    requested_minutes: int
    # Outputs
    assistant: str
    allow: bool
    minutes: int


def build_graph(settings: Settings, llm: BaseChatModel) -> StateGraph:
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            (
                "You are Athena, acting as a fair but firm productivity "
                "coach. You are evaluating a user's appeal to allow "
                "temporary access. Consider strictness (1..10) and the "
                "current timeblock goal. Be lenient at low strictness and "
                "strict at high strictness, but always explain. Return ONLY "
                "JSON with: {\"assistant\":string,\"allow\":boolean,"
                "\"minutes\":number}. "
                "If allowing, minutes should be minimal (1-60)."
            ),
        ),
        (
            "system",
            (
                "Context: strictness={strictness} | goal={goal} | "
                "host={host} path={path} title={title} "
                "package={package} activity={activity}"
            ),
        ),
        (
            "human",
            (
                "User justification: {user_justification}\n"
                "Requested minutes: {requested_minutes}"
            ),
        ),
    ])

    def evaluate(state: AppealState) -> AppealState:
        strict = get_current_strictness(
            settings, session_id=state.get("session_id")
        )
        goal = get_current_goal(settings, session_id=state.get("session_id"))
        chain = prompt | llm
        out = chain.invoke({
            "strictness": strict,
            "goal": goal,
            "host": state.get("host", ""),
            "path": state.get("path", ""),
            "title": state.get("title", ""),
            "package": state.get("package", ""),
            "activity": state.get("activity", ""),
            "user_justification": state.get("user_justification", ""),
            "requested_minutes": int(state.get("requested_minutes", 0)),
        })
        raw = (out.content or "").strip()  # type: ignore[attr-defined]
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"assistant": raw, "allow": False, "minutes": 0}
        state["assistant"] = str(data.get("assistant", ""))
        state["allow"] = bool(data.get("allow", False))
        state["minutes"] = int(data.get("minutes", 0))
        # Clamp minutes 0..15
        if state["minutes"] < 0:
            state["minutes"] = 0
        if state["minutes"] > 15:
            state["minutes"] = 15
        return state

    graph = StateGraph(AppealState)
    graph.add_node("evaluate", evaluate)
    graph.set_entry_point("evaluate")
    graph.add_edge("evaluate", END)
    return graph


REGISTRY.register(
    "appeals",
    AgentEntry(
        config=AgentConfig(
            name="Appeals Agent",
            description=(
                "Evaluate user appeals using strictness and current goal; "
                "returns allow + minutes."
            ),
            model_name='gpt-5',
        ),
        build_graph=build_graph,
    ),
)



