from __future__ import annotations

import json
from typing import Optional
import re
from enum import StrEnum
from pydantic import BaseModel
from urllib.parse import urlparse

from langgraph.graph import END, StateGraph
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage

from polymetis.celery import app as celery_app
from polymetis.config import Settings
from polymetis.tools.policies.schedule import (
    get_current_strictness,
    get_current_goal,
)
from polymetis.agents.registry import REGISTRY
from polymetis.agents.utils import BaseFlow
from polymetis.agents.prompts.guardian import classify_prompt
from polymetis.tools.registry import SENSITIVE_TOOLS
from polymetis.memory.vectorstore import MemoryDeps
from polymetis.tools.mongo_admin import _call_mongo  # noqa: F401
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

    def build_graph(self, settings: Settings, llm: BaseChatModel, memory: MemoryDeps) -> StateGraph:

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
            # Build policy.* tool surface and bind to the model
            policy_specs = [
                (name, spec)
                for name, spec in SENSITIVE_TOOLS.list().items()
                if name.startswith("policy.")
            ]
            # Sanitize tool names to comply with OpenAI pattern ^[a-zA-Z0-9_-]+$
            sanitized_to_original: dict[str, str] = {}
            tools_for_llm = []
            for name, spec in policy_specs:
                sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
                base = sanitized
                i = 1
                while sanitized in sanitized_to_original and sanitized_to_original[sanitized] != name:
                    sanitized = f"{base}_{i}"
                    i += 1
                sanitized_to_original[sanitized] = name
                tools_for_llm.append(
                    {
                        "type": "function",
                        "function": {
                            "name": sanitized,
                            "description": spec.description,
                            "parameters": spec.schema or {"type": "object"},
                        },
                    }
                )
            llm_with_tools = llm.bind_tools(tools_for_llm) if tools_for_llm else llm

            # Retrieve short context based on URL/app signals
            try:
                query = " ".join([
                    state.host or "",
                    state.title or "",
                    state.path or "",
                    state.activity or "",
                ]).strip()
                docs = memory.retriever.invoke(query) if query else []
                context = "\n\n".join([d.page_content for d in docs]) if docs else ""
            except Exception as e:
                logger.exception("retrieval failed: %s", e)
                context = ""

            # Render prompt to messages so we can inject tool results if needed
            messages = classify_prompt.format_messages(
                strictness=state.strictness,
                timeblock_goal=state.goal,
                host=state.host,
                app=state.app,
                path=state.path,
                activity=state.activity,
                title=state.title,
                context=context,
            )
            out = llm_with_tools.invoke(messages)

            # If the model calls tools, execute them and re-ask once
            if isinstance(out, AIMessage) and getattr(out, "tool_calls", None):
                tool_messages: list[ToolMessage] = []
                for call in out.tool_calls:
                    try:
                        name = str(call.get("name", ""))
                        registry_name = sanitized_to_original.get(name, name)
                        args = call.get("args") or {}
                        # Execute via registry
                        result = SENSITIVE_TOOLS.call(registry_name, args)
                        tool_messages.append(
                            ToolMessage(content=json.dumps(result), tool_call_id=call.get("id", ""))
                        )
                    except Exception as e:
                        logger.exception("tool execution failed: %s", e)
                        tool_messages.append(
                            ToolMessage(content=json.dumps({"error": str(e)}), tool_call_id=call.get("id", ""))
                        )
                out = llm_with_tools.invoke(messages + [out, *tool_messages])

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
            updated_state = state.model_copy(update={"classification": label})
            # No vector writes for guardian experimental
            return respond(updated_state)

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


# GuardianFlow()()
