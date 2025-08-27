from __future__ import annotations

import json
from typing import Literal, TypedDict
from urllib.parse import urlparse

from langgraph.graph import END, StateGraph
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from athena_server.config import Settings
from athena_server.policies.schedule import get_current_strictness, get_current_goal
from athena_server.agents.registry import REGISTRY, AgentConfig, AgentEntry


ClassificationLabel = Literal[
    "work",
    "neutral",
    "distraction",
    "unhealthy_habit",
]


class ClassifierState(TypedDict, total=False):
    # Inputs
    url: str
    title: str
    session_id: str

    # Derived
    host: str
    path: str
    activity: str

    # Outputs
    classification: ClassificationLabel
    should_block: bool


def build_graph(_settings: Settings, llm: BaseChatModel) -> StateGraph:
    """Build a simple sense -> classify -> compute decision graph.

    """

    prompt = ChatPromptTemplate.from_messages([
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
                "does not align with the goal, prefer 'distraction' when strictness is high.\n"
                "Return ONLY valid JSON shaped as:"
                " {\"classification\": "
                "\"work|neutral|distraction|unhealthy_habit\"}."
            ),
        ),
        (
            "human",
            "strictness={strictness}\n"
            "timeblock_goal={timeblock_goal}\n"
            "host={host}\npath={path}\nactivity={activity}\ntitle={title}",
        ),
    ])

    def sense(state: ClassifierState) -> ClassifierState:
        url_value = state.get("url", "") or ""
        parsed = urlparse(url_value)
        state["host"] = parsed.hostname or ""
        state["path"] = parsed.path or "/"
        # If app URL (e.g., app://com.pkg/ActivityName), expose activity
        if parsed.scheme in ("app", "android-app"):
            act = (parsed.path or "").lstrip("/")
            state["activity"] = act
        return state

    def classify(state: ClassifierState) -> ClassifierState:
        chain = prompt | llm
        # inject strictness from schedule
        session_id = state.get("session_id")
        strict = get_current_strictness(_settings, session_id=session_id)
        goal = get_current_goal(_settings, session_id=session_id)
        out = chain.invoke({
            "strictness": strict,
            "timeblock_goal": goal,
            "host": state.get("host", ""),
            "path": state.get("path", ""),
            "activity": state.get("activity", ""),
            "title": state.get("title", ""),
        })
        raw = (out.content or "").strip()  # type: ignore[attr-defined]
        label: ClassificationLabel = "neutral"
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
            # Fallback: try to coerce simple string responses
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

    def decide(state: ClassifierState) -> ClassifierState:
        label = state.get("classification", "neutral")
        state["should_block"] = bool(
            label in ("distraction", "unhealthy_habit")
        )
        return state

    def project(state: ClassifierState) -> ClassifierState:
        # Return only the requested outputs
        return {
            "classification": state.get("classification", "neutral"),
            "should_block": bool(state.get("should_block", False)),
        }

    graph = StateGraph(ClassifierState)
    graph.add_node("sense", sense)
    graph.add_node("classify", classify)
    graph.add_node("decide", decide)
    graph.add_node("project", project)
    graph.set_entry_point("sense")
    graph.add_edge("sense", "classify")
    graph.add_edge("classify", "decide")
    graph.add_edge("decide", "project")
    graph.add_edge("project", END)
    return graph


# Register the classifier agent
REGISTRY.register(
    "classifier",
    AgentEntry(
        config=AgentConfig(
            name="Distraction Classifier",
            description=(
                "Classify a page as work/neutral/distraction/"
                "unhealthy_habit and return should_block (no strict mode)."
            ),
            model_name="gpt-5-nano",
        ),
        build_graph=build_graph,
    ),
)
