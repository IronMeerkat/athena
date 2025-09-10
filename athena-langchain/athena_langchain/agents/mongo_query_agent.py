from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
import re

from pydantic import BaseModel
from langgraph.graph import END, StateGraph
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage

from athena_logging import get_logger
from athena_langchain.config import Settings
from athena_langchain.agents.utils import BaseFlow
from athena_langchain.memory.vectorstore import MemoryDeps
from athena_langchain.tools.registry import SENSITIVE_TOOLS
from athena_langchain.registry import SENSITIVE_AGENTS as REGISTRY
from athena_langchain.tools.mongo_admin import _call_mongo  # noqa: F401


logger = get_logger(__name__)


class AgentState(BaseModel, frozen=False):
    instruction: str = ""
    collection: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    assistant: str = ""
    result: Optional[Any] = None
    session_id: str = ""


SYSTEM_PROMPT = (
    "You are an expert MongoDB and PyMongo assistant. You have access to a single tool 'mongo.admin' "
    "which accepts JSON arguments and performs MongoDB admin and CRUD operations on the 'sensitive' database. "
    "Use this tool to satisfy the user's instruction. Prefer precise filters, projections, and indexes when appropriate. "
    "You are NOT allowed to drop or recreate predefined collections: User, Location, Schedule. Do not attempt schema changes. "
    "When you use the tool, ensure arguments match the tool's JSON schema: set 'op' and include fields like 'collection', 'filter', 'update', 'document', 'documents', 'pipeline', 'limit', 'skip', 'sort', etc., as needed. "
    "Keep explanations brief. Return a short summary of what you did and key results."
)


def _build_messages(instruction: str, collection: Optional[str], args: Optional[Dict[str, Any]]):
    messages: List[Dict[str, str]] = [
        {"type": "system", "content": SYSTEM_PROMPT},
        {"type": "human", "content": json.dumps({
            "instruction": instruction,
            "collection": collection,
            "args": args or {},
        })},
    ]
    return messages


class MongoQueryFlow(BaseFlow):
    registry = REGISTRY
    name = "mongo_query"
    description = "Agent that writes and executes MongoDB/PyMongo queries via the mongo.admin tool."
    model_name = "gpt-5"
    temperature = 0.1

    def build_graph(self, settings: Settings, llm: BaseChatModel, memory: MemoryDeps) -> StateGraph:
        # Prepare tool surface for the LLM
        spec = SENSITIVE_TOOLS.list().get("mongo.admin")
        tools_for_llm: List[Dict[str, Any]] = []
        sanitized_to_original: Dict[str, str] = {}
        if spec is not None:
            name = "mongo.admin"
            sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
            sanitized_to_original[sanitized] = name
            tools_for_llm = [
                {
                    "type": "function",
                    "function": {
                        "name": sanitized,
                        "description": spec.description,
                        "parameters": spec.schema or {"type": "object"},
                    },
                }
            ]
        llm_with_tools = llm.bind_tools(tools_for_llm) if tools_for_llm else llm

        def plan_and_execute(state: AgentState) -> AgentState:
            instruction = (state.instruction or "").strip()
            collection = state.collection
            args = state.args or {}
            messages = _build_messages(instruction, collection, args)

            last_tool_result: Any = None
            # Allow up to 3 tool-use iterations
            rounds = 0
            out = llm_with_tools.invoke(messages)
            while isinstance(out, AIMessage) and getattr(out, "tool_calls", None) and rounds < 3:
                tool_messages: List[ToolMessage] = []
                for call in out.tool_calls:
                    try:
                        name = str(call.get("name") or "")
                        registry_name = sanitized_to_original.get(name, name)
                        call_args = call.get("args") or {}
                        result = SENSITIVE_TOOLS.call(registry_name, call_args)
                        last_tool_result = result
                        tool_messages.append(ToolMessage(content=json.dumps(result), tool_call_id=call.get("id", "")))
                    except Exception as e:  # noqa: BLE001
                        logger.exception("mongo.admin call failed: %s", e)
                        tool_messages.append(ToolMessage(content=json.dumps({"error": str(e)}), tool_call_id=call.get("id", "")))

                logger.info(f"tool_messages: {tool_messages}" )
                out = llm_with_tools.invoke(messages + [out, *tool_messages])
                logger.info(f"out: {out}" )
                rounds += 1

            # Build assistant text
            text: str
            if isinstance(out, AIMessage):
                text = out.content if isinstance(out.content, str) else str(out)
            else:
                text = str(out)

            # # Optionally write a lightweight memory entry
            # try:
            #     if instruction:
            #         memory.vectorstore.add_texts(
            #             [f"mongo_query: {instruction}"],
            #             metadatas=[{"agent": "mongo_query", "session_id": state.session_id}],
            #         )
            # except Exception as e:  # noqa: BLE001
            #     logger.exception("vector memory write failed")

            return state.model_copy(update={"assistant": text.strip(), "result": last_tool_result})

        graph = StateGraph(AgentState)
        graph.add_node("plan_and_execute", plan_and_execute)
        graph.set_entry_point("plan_and_execute")
        graph.add_edge("plan_and_execute", END)
        return graph


MongoQueryFlow()()


