from __future__ import annotations

import json
from typing import Optional
from enum import StrEnum
from pydantic import BaseModel
from urllib.parse import urlparse

from langgraph.graph import END, StateGraph
from langchain_core.language_models.chat_models import BaseChatModel

from athena_langchain.celery import app as celery_app
from athena_langchain.config import Settings
from athena_langchain.tools.policies.schedule import (
    get_current_strictness,
    get_current_goal,
)
from athena_langchain.agents.registry import REGISTRY
from athena_langchain.agents.utils import BaseFlow
from athena_langchain.agents.prompts.guardian import classify_prompt


from athena_logging import get_logger

logger = get_logger(__name__)

class Decision(StrEnum):
    ALLOW = "allow"
    NUDGE = "nudge"
    BLOCK = "block"
    APPEAL = "appeal"


class Classification(StrEnum):
    WORK = "work"
    NEUTRAL = "neutral"
    DISTRACTION = "distraction"
    UNHEALTHY_HABIT = "unhealthy_habit"


class GuardianState(BaseModel, frozen=False):
    # Inputs
    event_id: str = ""
    device_id: str = ""
    session_id: Optional[str] = None
    url: Optional[str] = None
    app: str = ""
    title: str = ""

    # Derived context
    host: str = ""
    path: str = "/"
    package: str = ""
    activity: str = ""
    strictness: int = 10
    goal: str = ""

    # Classification
    classification: Classification = Classification.UNHEALTHY_HABIT

    # Output decision
    decision: Decision = Decision.BLOCK
    permit_ttl: int = 0
    appeal_available: bool = False
    message: str = ""


class GuardianFlow(BaseFlow):
    registry = REGISTRY
    name = "guardian"
    description = (
        "Fast allow/nudge/block/appeal based on classification and"
        " strictness."
    )
    model_name = "gpt-5-nano"
    temperature = 0.0

    def build_graph(self, settings: Settings, llm: BaseChatModel) -> StateGraph:

        def respond(state: GuardianState) -> GuardianState:
            celery_app.send_task(
                "gateway.dispatch_push",
                args=[state.device_id, state.title, state.message, "guardian", state.model_dump()],
                queue="gateway",
            )
            return state

        def assemble(state: GuardianState) -> GuardianState:

            # logger.info(f"Assembling state: {state}")
            # Derive URL parts and Android hints
            url_value = state.url or ""
            parsed = urlparse(url_value)
            updated = state.model_copy(update={
                "host": parsed.hostname or "",
                "path": parsed.path or "/",
            })
            # Interpret app package if provided
            pkg = (state.app or "").strip()
            updated = updated.model_copy(update={"package": pkg})
            if parsed.scheme in ("app", "android-app"):
                act = (parsed.path or "").lstrip("/")
                updated = updated.model_copy(update={"activity": act})
            # Fetch current policy context
            sid: Optional[str] = updated.session_id
            updated = updated.model_copy(update={
                "strictness": get_current_strictness(settings, session_id=sid),
                "goal": get_current_goal(settings, session_id=sid),
            })
            return respond(updated)

        def classify(state: GuardianState) -> GuardianState:
            chain = classify_prompt | llm
            out = chain.invoke({
                "strictness": state.strictness,
                "timeblock_goal": state.goal,
                "host": state.host,
                "app": state.app,
                "path": state.path,
                "activity": state.activity,
                "title": state.title,
            })

            data = json.loads(out.content)
            try:
                raw_label = data.get("classification", Classification.NEUTRAL.value)
                label: Classification = Classification(raw_label)
            except (ValueError, TypeError):
                logger.warning(
                    "Unknown classification %r; defaulting to NEUTRAL",
                    data.get("classification"),
                )
                label = Classification.NEUTRAL
            return respond(state.model_copy(update={"classification": label}))

        def decide(state: GuardianState) -> GuardianState:
            # strict = int(state.strictness)
            strict = 7
            # label = state.classification
            label = Classification.UNHEALTHY_HABIT

            # Default outputs
            updated = state.model_copy(update={
                "permit_ttl": 0,
                "appeal_available": False,
                "message": "",
            })

            if label == Classification.WORK:
                updated = updated.model_copy(update={"decision": Decision.ALLOW})
                return respond(updated)

            if label == Classification.NEUTRAL:
                if strict <= 3:
                    updated = updated.model_copy(update={"decision": Decision.ALLOW})
                elif strict <= 6:
                    updated = updated.model_copy(update={
                        "decision": Decision.NUDGE,
                        "permit_ttl": 2,
                        "message": "2 minutes, then back to focus?",
                    })
                else:
                    updated = updated.model_copy(update={
                        "decision": Decision.BLOCK,
                        "appeal_available": True,
                    })
                return respond(updated)

            # distraction / unhealthy_habit
            if strict <= 2:
                updated = updated.model_copy(update={
                    "decision": Decision.NUDGE,
                    "permit_ttl": 2,
                    "message": "2 minutes, then close?",
                })
            elif strict <= 6:
                updated = updated.model_copy(update={
                    "decision": Decision.BLOCK,
                    "appeal_available": True,
                })
            elif strict <= 8:
                updated = updated.model_copy(update={
                    "decision": Decision.APPEAL,
                    "appeal_available": True,
                })
            else:
                updated = updated.model_copy(update={
                    "decision": Decision.BLOCK,
                    "appeal_available": False,
                })

            logger.info(f"Decided: {updated}")
            return respond(updated)

        def project(state: GuardianState) -> GuardianState:
            logger.info("Projecting state: %s", state)
            return state

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


GuardianFlow()()
