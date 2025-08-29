from __future__ import annotations

import json
from typing import Literal, TypedDict, Optional
from urllib.parse import urlparse

from langgraph.graph import END, StateGraph
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from athena_langchain.config import Settings
from athena_langchain.tools.policies.schedule import (
    get_current_strictness,
    get_current_goal,
)
from athena_langchain.agents.registry import REGISTRY, AgentConfig, AgentEntry


import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

Decision = Literal["allow", "nudge", "block", "appeal"]
Classification = Literal["work", "neutral", "distraction", "unhealthy_habit"]


class GuardianState(TypedDict, total=False):
    # Inputs
    event_id: str
    session_id: str
    url: str
    app: str
    title: str

    # Derived context
    host: str
    path: str
    package: str
    activity: str
    strictness: int
    goal: str

    # Classification
    classification: Classification

    # Output decision
    decision: Decision
    permit_ttl: int
    appeal_available: bool
    message: str


def build_graph(settings: Settings, llm: BaseChatModel) -> StateGraph:
    classify_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            (
                "You are a focused productivity classifier. "
                "Given a page host/path/title or an Android package/activity, "
                "choose exactly one classification from this set:\n"
                "- work\n- neutral\n- distraction\n- unhealthy_habit\n\n"
                "Use the provided strictness (1..10) as your bias towards "
                "blocking: 10=extremely strict, 1=very lenient.\n"
                "Also consider the current timeblock goal. If the page/app "
                "does not align with the goal, prefer 'distraction' "
                "at high strictness.\n"
                "Return ONLY valid JSON shaped as:"
                " {{\"classification\": "
                "\"work|neutral|distraction|unhealthy_habit\"}}."
            ),
        ),
        (
            "human",
            (
                "strictness={strictness}\n"
                "timeblock_goal={timeblock_goal}\n"
                "host={host}\n"
                "path={path}\n"
                "activity={activity}\n"
                "title={title}"
            ),
        ),
    ])

    def assemble(state: GuardianState) -> GuardianState:
        # Derive URL parts and Android hints
        url_value = state.get("url", "") or ""
        parsed = urlparse(url_value)
        state["host"] = parsed.hostname or ""
        state["path"] = parsed.path or "/"
        # Interpret app package if provided
        pkg = (state.get("app") or "").strip()
        state["package"] = pkg
        if parsed.scheme in ("app", "android-app"):
            act = (parsed.path or "").lstrip("/")
            state["activity"] = act
        # Fetch current policy context
        sid: Optional[str] = state.get("session_id")
        state["strictness"] = get_current_strictness(settings, session_id=sid)
        state["goal"] = get_current_goal(settings, session_id=sid)
        return state

    def classify(state: GuardianState) -> GuardianState:
        chain = classify_prompt | llm
        out = chain.invoke({
            "strictness": state.get("strictness", 5),
            "timeblock_goal": state.get("goal", ""),
            "host": state.get("host", ""),
            "path": state.get("path", "/"),
            "activity": state.get("activity", ""),
            "title": state.get("title", ""),
        })
        raw = (out.content or "").strip()  # type: ignore[attr-defined]
        label: Classification = "neutral"
        try:
            data = json.loads(raw)
            candidate = str(data.get("classification", "")).strip().lower()
            if candidate in {
                "work",
                "neutral",
                "distraction",
                "unhealthy_habit",
            }:
                label = candidate  # type: ignore[assignment]
        except json.JSONDecodeError:
            low = raw.lower()
            for c in (
                "work",
                "neutral",
                "distraction",
                "unhealthy_habit",
            ):
                if c in low:
                    label = c  # type: ignore[assignment]
                    break
        state["classification"] = label
        return state

    def decide(state: GuardianState) -> GuardianState:
        strict = int(state.get("strictness", 5))
        label = state.get("classification", "neutral")

        # Default outputs
        state["permit_ttl"] = 0
        state["appeal_available"] = False
        state["message"] = ""

        if label == "work":
            state["decision"] = "allow"
            return state

        if label == "neutral":
            if strict <= 3:
                state["decision"] = "allow"
            elif strict <= 6:
                state["decision"] = "nudge"
                state["permit_ttl"] = 2
                state["message"] = "2 minutes, then back to focus?"
            else:
                state["decision"] = "block"
                state["appeal_available"] = True
            return state

        # distraction / unhealthy_habit
        if strict <= 2:
            state["decision"] = "nudge"
            state["permit_ttl"] = 2
            state["message"] = "2 minutes, then close?"
        elif strict <= 6:
            state["decision"] = "block"
            state["appeal_available"] = True
        elif strict <= 8:
            state["decision"] = "appeal"
            state["appeal_available"] = True
        else:
            state["decision"] = "block"
            state["appeal_available"] = False
        return state

    def project(state: GuardianState) -> GuardianState:
        logger.info(f"Projecting state: {state}")
        return {
            "event_id": state.get("event_id", ""),
            "decision": state.get("decision", "allow"),
            "permit_ttl": int(state.get("permit_ttl", 0)),
            "appeal_available": bool(state.get("appeal_available", False)),
            "message": state.get("message", ""),
        }

    graph = StateGraph(GuardianState)
    graph.add_node("assemble", assemble)
    graph.add_node("classify", classify)
    graph.add_node("decide", decide)
    graph.add_node("project", project)
    graph.set_entry_point("assemble")
    graph.add_edge("assemble", "classify")
    graph.add_edge("classify", "decide")
    graph.add_edge("decide", "project")
    graph.add_edge("project", END)
    return graph


REGISTRY.register(
    "guardian",
    AgentEntry(
        config=AgentConfig(
            name="Distraction Guardian",
            description=(
                "Fast allow/nudge/block/appeal based on classification and "
                "strictness."
            ),
            model_name='gpt-5-nano',
        ),
        build_graph=build_graph,
    ),
)
