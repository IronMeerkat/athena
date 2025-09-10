from __future__ import annotations
"""
Policy tools exposed via the ToolRegistry.
This package registers schedule policy helpers as callable tools so that
agents (and the MCP server) can invoke them in a uniform way.
"""

from athena_langchain.tools.registry import (
    SENSITIVE_TOOLS as TOOL_REGISTRY,
    ToolSpec,
)
from athena_langchain.tools.policies.schedule import (
    save_schedule,
    load_schedule,
    get_current_strictness,
    get_current_goal,
)
from athena_langchain.config import Settings


def _schedule_get(args: dict) -> list[dict]:
    settings = Settings()
    user_key = str(args.get("user_key", ""))
    return load_schedule(settings, session_id=user_key)


def _schedule_set(args: dict) -> bool:
    settings = Settings()
    user_key = str(args.get("user_key", ""))
    schedule = args.get("schedule") or []
    save_schedule(settings, schedule, session_id=user_key)
    return True


def _strictness_get(args: dict) -> int:
    settings = Settings()
    user_key = str(args.get("user_key", ""))
    return get_current_strictness(settings, session_id=user_key)


def _goal_get(args: dict) -> str:
    settings = Settings()
    user_key = str(args.get("user_key", ""))
    return get_current_goal(settings, session_id=user_key)


# Register tool specs
TOOL_REGISTRY.register(
    ToolSpec(
        name="policy.schedule_get",
        description=(
            "Get the saved schedule for a given user_key "
            "(session id)."
        ),
        schema={
            "type": "object",
            "properties": {"user_key": {"type": "string"}},
            "required": ["user_key"],
        },
    ),
    _schedule_get,
)

TOOL_REGISTRY.register(
    ToolSpec(
        name="policy.schedule_set",
        description=(
            "Set the schedule for a given user_key (session id)."
        ),
        schema={
            "type": "object",
            "properties": {
                "user_key": {"type": "string"},
                # Schedule is an array of blocks; keep schema permissive per backend
                "schedule": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["user_key", "schedule"],
        },
    ),
    _schedule_set,
)

TOOL_REGISTRY.register(
    ToolSpec(
        name="policy.strictness_get",
        description=(
            "Get current strictness derived from the schedule at now()."
        ),
        schema={
            "type": "object",
            "properties": {"user_key": {"type": "string"}},
            "required": ["user_key"],
        },
    ),
    _strictness_get,
)

TOOL_REGISTRY.register(
    ToolSpec(
        name="policy.goal_get",
        description=(
            "Get the current timeblock goal from the schedule at now()."
        ),
        schema={
            "type": "object",
            "properties": {"user_key": {"type": "string"}},
            "required": ["user_key"],
        },
    ),
    _goal_get,
)


