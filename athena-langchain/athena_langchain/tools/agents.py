from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from langgraph.graph import StateGraph
from langchain_core.language_models.chat_models import BaseChatModel

from athena_logging import get_logger
from athena_langchain.config import Settings
from athena_langchain.memory.vectorstore import MemoryDeps, create_memory_deps
from athena_langchain.registry import SENSITIVE_AGENTS as REGISTRY
from athena_langchain.tools.registry import (
    SENSITIVE_TOOLS as TOOL_REGISTRY,
    ToolSpec,
)


logger = get_logger(__name__)


def _build_runnable(agent_id: str, settings: Settings) -> Tuple[StateGraph, Any]:
    entry = REGISTRY.get(agent_id)
    llm = REGISTRY.build_llm(settings, agent_id)
    memory = create_memory_deps(settings)
    graph = entry.build_graph(settings, llm, memory)
    runnable = graph.compile()
    return graph, runnable


def _agents_call(args: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke an agent by id with a provided payload and return the result.

    Args expected:
      - agent_id: string (registered agent name)
      - payload: dict (fields matching the agent's state model)
    """
    settings = Settings()
    agent_id = str(args["agent_id"]).strip()
    payload = args.get("payload") or {}

    graph, runnable = _build_runnable(agent_id, settings)
    try:
        result = runnable.invoke(payload)

        if hasattr(result, "model_dump"):
            try:
                result = result.model_dump()
            except Exception:
                logger.exception("model_dump failed")
        if isinstance(result, dict):
            return result
        return {"assistant": str(result)}
    except Exception as e:  # noqa: BLE001
        logger.exception("agents.call failed: %s", e)
        return {"assistant": f"error: {e}"}

def _agents_list(_args: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """List registered agents and their metadata (name, description)."""
    entries = REGISTRY.list()
    return {
        agent_id: {
            "name": cfg.name,
            "description": cfg.description,
        }
        for agent_id, cfg in entries.items()
    }


def _agents_dialogue(args: Dict[str, Any]) -> Dict[str, Any]:
    """Run a back-and-forth dialogue between two agents.

    Args expected:
      - a_agent_id: string
      - b_agent_id: string
      - a_payload: object (initial payload for A)
      - b_payload: object (initial payload for B)
      - max_rounds: integer (number of A->B->A turns; default 3)
      - a_output_key: string (field in A result to send to B; default 'assistant')
      - b_output_key: string (field in B result to send to A; default 'assistant')
      - a_input_key: string (field in B payload to set; default 'user_message')
      - b_input_key: string (field in A payload to set; default 'user_message')
    """
    settings = Settings()
    a_id = str(args["a_agent_id"]).strip()
    b_id = str(args["b_agent_id"]).strip()
    a_payload: Dict[str, Any] = dict(args.get("a_payload") or {})
    b_payload: Dict[str, Any] = dict(args.get("b_payload") or {})
    max_rounds = int(args.get("max_rounds", 3) or 3)

    a_out_key = str(args.get("a_output_key", "assistant") or "assistant")
    b_out_key = str(args.get("b_output_key", "assistant") or "assistant")
    a_in_key = str(args.get("a_input_key", "user_message") or "user_message")
    b_in_key = str(args.get("b_input_key", "user_message") or "user_message")

    # Prepare runnables once per agent
    _, a_runnable = _build_runnable(a_id, settings)
    _, b_runnable = _build_runnable(b_id, settings)

    transcript: List[Dict[str, Any]] = []

    last_a_result: Optional[Dict[str, Any]] = None
    last_b_result: Optional[Dict[str, Any]] = None

    for _ in range(max_rounds):
        # A speaks
        try:
            a_result = a_runnable.invoke(a_payload)
            if not isinstance(a_result, dict):
                a_result = {"assistant": str(a_result)}
        except Exception as e:  # noqa: BLE001
            logger.exception("Dialogue: agent A (%s) failed: %s", a_id, e)
            a_result = {"assistant": f"error: {e}"}
        transcript.append({"speaker": "A", **a_result})
        last_a_result = a_result
        # Feed A's output to B
        b_payload = dict(b_payload)
        b_payload[b_in_key] = str(a_result.get(a_out_key, ""))

        # B responds
        try:
            b_result = b_runnable.invoke(b_payload)
            if not isinstance(b_result, dict):
                b_result = {"assistant": str(b_result)}
        except Exception as e:  # noqa: BLE001
            logger.exception("Dialogue: agent B (%s) failed: %s", b_id, e)
            b_result = {"assistant": f"error: {e}"}
        transcript.append({"speaker": "B", **b_result})
        last_b_result = b_result
        # Feed B's output back to A for next round
        a_payload = dict(a_payload)
        a_payload[a_in_key] = str(b_result.get(b_out_key, ""))

    return {
        "transcript": transcript,
        "a_result": last_a_result,
        "b_result": last_b_result,
    }


# Register tool specs
TOOL_REGISTRY.register(
    ToolSpec(
        name="agents.list",
        description=(
            "List registered agents (id, name, description)."
        ),
        schema={
            "type": "object",
            "properties": {},
        },
    ),
    _agents_list,
)

TOOL_REGISTRY.register(
    ToolSpec(
        name="agents.call",
        description=(
            "Invoke a registered agent by id with a payload. "
            "Input: {agent_id, payload}. Returns the agent's result."
        ),
        schema={
            "type": "object",
            "properties": {
                "agent_id": {"type": "string"},
                "payload": {"type": "object"},
            },
            "required": ["agent_id"],
        },
    ),
    _agents_call,
)

TOOL_REGISTRY.register(
    ToolSpec(
        name="agents.dialogue",
        description=(
            "Run a back-and-forth conversation between two agents for N rounds. "
            "Defaults to wiring assistant->user_message between turns."
        ),
        schema={
            "type": "object",
            "properties": {
                "a_agent_id": {"type": "string"},
                "b_agent_id": {"type": "string"},
                "a_payload": {"type": "object"},
                "b_payload": {"type": "object"},
                "max_rounds": {"type": "integer"},
                "a_output_key": {"type": "string"},
                "b_output_key": {"type": "string"},
                "a_input_key": {"type": "string"},
                "b_input_key": {"type": "string"},
            },
            "required": ["a_agent_id", "b_agent_id"],
        },
    ),
    _agents_dialogue,
)


