from __future__ import annotations

import json
from typing import List
import re
from pydantic import BaseModel

from langgraph.graph import END, StateGraph
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage

from athena_logging import get_logger

from polymetis.config import Settings
from polymetis.agents.registry import REGISTRY
from polymetis.agents.utils import BaseFlow
from polymetis.tools.policies.schedule import save_schedule
from polymetis.tools.registry import SENSITIVE_TOOLS
from polymetis.memory.chat_history import get_session_history_factory
from polymetis.agents.prompts.goals import goals_prompt as prompt
from polymetis.memory.vectorstore import MemoryDeps

logger = get_logger(__name__)


class AgentState(BaseModel, frozen=False):
    session_id: str = "default"
    user_message: str = ""
    assistant: str = ""
    schedule: List[dict] = []


class GoalsFlow(BaseFlow):
    registry = REGISTRY
    name = "goals_scheduler"
    description = (
        "Discuss goals, update memories, create schedule with per-block"
        " strictness (1-10)."
    )
    model_name = "gpt-5"
    temperature = 0.8

    def build_graph(
        self, settings: Settings, llm: BaseChatModel, memory: MemoryDeps
    ) -> StateGraph:

        def converse(state: AgentState) -> AgentState:
            # Retrieve context for goals discussion
            try:
                docs = memory.retriever.invoke(state.user_message) if state.user_message else []
                context = "\n\n".join([d.page_content for d in docs]) if docs else ""
            except Exception as e:
                # Never block; just log and proceed
                logger.exception("retrieval failed")
                context = ""

            # Bind agents.* tools so the model can call other agents
            agent_specs = [
                (name, spec)
                for name, spec in SENSITIVE_TOOLS.list().items()
                if name.startswith("agents.")
            ]
            # Sanitize tool names for OpenAI pattern ^[a-zA-Z0-9_-]+$
            sanitized_to_original: dict[str, str] = {}
            tools_for_llm = []
            for name, spec in agent_specs:
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

            # Pull short chat history for memory
            session_id = state.session_id or "default"
            hist_factory = get_session_history_factory(settings)
            history = hist_factory(session_id)
            hist_msgs = history.messages[-10:]
            history_str = "\n".join(
                [f"{m.type}: {getattr(m, 'content', '')}" for m in hist_msgs]
            )
            messages = prompt.format_messages(
                history=history_str,
                user_message=state.user_message,
                context=context,
            )
            out = llm_with_tools.invoke(messages)
            if isinstance(out, AIMessage) and getattr(out, "tool_calls", None):
                tool_messages: list[ToolMessage] = []
                for call in out.tool_calls:
                    try:
                        name = str(call.get("name") or "")
                        registry_name = sanitized_to_original.get(name, name)
                        args = call.get("args") or {}
                        result = SENSITIVE_TOOLS.call(registry_name, args)
                        tool_messages.append(
                            ToolMessage(content=json.dumps(result), tool_call_id=call.get("id", ""))
                        )
                    except Exception as e:  # noqa: BLE001
                        logger.exception("goals tool exec failed: %s", e)
                        tool_messages.append(
                            ToolMessage(content=json.dumps({"error": str(e)}), tool_call_id=call.get("id", ""))
                        )
                out = llm_with_tools.invoke(messages + [out, *tool_messages])

            data = json.loads(out.content)

            assistant = data["assistant"]
            schedule = data["schedule"]

            # Persist schedule (no vector writes here)
            sid = state.session_id
            save_schedule(settings, schedule, session_id=sid)

            # Append to chat history
            history.add_user_message(state.user_message)
            history.add_ai_message(assistant)

            return state.model_copy(update={
                "assistant": assistant,
                "schedule": schedule,
            })

        graph = StateGraph(AgentState)
        graph.add_node("converse", converse)
        graph.set_entry_point("converse")
        graph.add_edge("converse", END)
        return graph


GoalsFlow()()
