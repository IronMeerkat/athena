from __future__ import annotations

from typing import Dict, List, Any
import re
from pydantic import BaseModel, Field

from langgraph.graph import END, StateGraph
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage, SystemMessage

from athena_langchain.config import Settings
from athena_langchain.registry import SENSITIVE_AGENTS as REGISTRY
from athena_langchain.agents.utils import BaseFlow
from athena_langchain.memory.chat_history import (
    get_session_history_factory,
)
from athena_langchain.celery import app as celery_app
from athena_langchain.memory.vectorstore import MemoryDeps
from athena_logging import get_logger
from athena_langchain.tools.registry import SENSITIVE_TOOLS
from athena_langchain.tools.mongo_admin import _call_mongo  # noqa: F401
from athena_langchain.agents.utils import _json_safe
from bson import ObjectId, Decimal128
from bson.binary import Binary
from datetime import datetime
import base64
import json

logger = get_logger(__name__)


class AgentState(BaseModel, frozen=False):
    user_message: str = ""
    text: str = ""
    assistant: str = ""
    connect: bool = False
    disconnect: bool = False
    convo_history: List[Dict[str, str]] = []
    session_id: str = ""
    # Orchestration fields
    needs_tools: bool = False
    incoming_text: str = ""
    context: str = ""
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    tool_iterations: int = 0
    sanitized_to_original: Dict[str, str] = Field(default_factory=dict)
    tools_for_llm: List[Dict[str, Any]] = Field(default_factory=list)
    history_snapshot: Dict[str, List[Dict[str, str]]] = Field(default_factory=dict)


class JournalingFlow(BaseFlow):
    registry = REGISTRY
    name = "journaling"
    description = (
        "A lightweight journaling companion that reflects and asks questions."
    )
    model_name = "gpt-5"
    temperature = 0.8

    def build_graph(
        self, settings: Settings, llm: BaseChatModel, memory: MemoryDeps
    ) -> StateGraph:
        from athena_langchain.agents.prompts.journaling import (
            journaling_prompt as prompt,
        )

        def to_lc_messages(items: List[Dict[str, str]]) -> List[BaseMessage]:
            messages: List[BaseMessage] = []
            for item in items:
                role = (item.get("role") or "").lower()
                content = (item.get("content") or item.get("text") or "")
                if not content:
                    continue
                if role == "assistant":
                    messages.append(AIMessage(content=content))
                else:
                    messages.append(HumanMessage(content=content))
            return messages

        def bind_tools_and_specs() -> tuple[list, dict]:
            sanitized_to_original: Dict[str, str] = {}
            tools_for_llm_local = []
            for t_name, t_spec in SENSITIVE_TOOLS.list().items():
                sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", t_name)
                base = sanitized
                counter = 1
                while (
                    sanitized in sanitized_to_original
                    and sanitized_to_original[sanitized] != t_name
                ):
                    sanitized = f"{base}_{counter}"
                    counter += 1
                sanitized_to_original[sanitized] = t_name
                tools_for_llm_local.append(
                    {
                        "type": "function",
                        "function": {
                            "name": sanitized,
                            "description": t_spec.description,
                            "parameters": t_spec.schema or {"type": "object"},
                        },
                    }
                )
            return tools_for_llm_local, sanitized_to_original

        def node_decide(state: AgentState) -> AgentState:
            incoming_text = str(state.user_message or state.text or "").strip()
            session_id = str(state.session_id or "").strip()
            state.incoming_text = incoming_text
            history_factory = get_session_history_factory(settings)
            redis_history = history_factory(session_id)

            # Connection bootstrap
            if state.connect:
                convo_history = state.convo_history
                if convo_history:
                    redis_history.clear()
                    for message in to_lc_messages(convo_history):
                        redis_history.add_message(message)

            # New chat greeting or /start
            if not redis_history.messages or incoming_text == "/start":
                first = "Hi, I'm Athena. What's on your mind today?"
                state.assistant = first
                state.text = first
                state.needs_tools = False
                return state

            # Disconnect snapshot
            if state.disconnect:
                hist_items: List[Dict[str, str]] = []
                for m in redis_history.messages:
                    role = "assistant" if isinstance(m, AIMessage) else "user"
                    hist_items.append({"role": role, "content": str(m.content)})
                state.history_snapshot = {"messages": hist_items}
                state.needs_tools = False
                return state

            # Empty input: ack with empty assistant
            if not incoming_text:
                state.assistant = ""
                state.text = ""
                state.needs_tools = False
                return state

            # Build LC history for context (append user message)
            lc_history: List[BaseMessage] = []
            try:
                if redis_history is not None:
                    redis_history.add_user_message(incoming_text)
                    lc_history = list(redis_history.messages)
            except Exception as e:  # noqa: BLE001
                logger.exception("history fallback error: %s", e)
                lc_history = to_lc_messages(state.convo_history or [])

            # Retrieve context
            try:
                docs = (
                    memory.retriever.invoke(incoming_text) if incoming_text else []
                )
                context_text = "\n\n".join([d.page_content for d in docs]) if docs else ""
            except Exception as e:  # noqa: BLE001
                logger.exception("retrieval failed")
                context_text = ""
            state.context = context_text

            # Tools and initial pass
            tools_for_llm_local, sanitized_to_original = bind_tools_and_specs()
            state.tools_for_llm = tools_for_llm_local
            state.sanitized_to_original = sanitized_to_original

            llm_base = llm.bind(reasoning={"effort": "high"})
            llm_with_tools = (
                llm_base.bind_tools(tools_for_llm_local) if tools_for_llm_local else llm_base
            )
            messages = prompt.format_messages(
                user_message=incoming_text,
                history=lc_history,
                context=context_text,
            )
            out = llm_with_tools.invoke(messages)

            if isinstance(out, AIMessage) and getattr(out, "tool_calls", None):
                # Prepare to enter tool loop
                state.tool_calls = [
                    {"id": c.get("id", ""), "name": c.get("name"), "args": c.get("args", {})}
                    for c in out.tool_calls
                ]
                state.needs_tools = True
                # Keep a draft text if any
                if out.content and isinstance(out.content, str):
                    state.text = out.content
            else:
                # Direct answer path
                if isinstance(out, AIMessage):
                    if out.content and isinstance(out.content, str):
                        state.text = out.content
                    elif isinstance(out.content, list):
                        list_text = [i['text'] for i in out.content if i['type'] == 'text']
                        state.text = "\n".join(list_text)
                    else:
                        state.text = ""
                else:
                    state.text = str(getattr(out, "content", ""))
                state.needs_tools = False

            return state

        def node_answer_direct(state: AgentState) -> AgentState:
            # Nothing to do; text already set during decide
            return state

        def _build_messages_for_session(session_id: str, state: AgentState) -> List[BaseMessage]:
            history_factory = get_session_history_factory(settings)
            redis_history = history_factory(session_id)
            try:
                lc_history_local = list(redis_history.messages)
            except Exception:
                lc_history_local = to_lc_messages(state.convo_history or [])
            messages_local = prompt.format_messages(
                user_message=state.incoming_text,
                history=lc_history_local,
                context=state.context,
            )
            return messages_local

        def node_tool_loop(state: AgentState) -> AgentState:
            session_id = str(state.session_id or "").strip()
            tools_for_llm_local = state.tools_for_llm
            llm_base = llm.bind(reasoning={"effort": "high"})
            llm_with_tools = (
                llm_base.bind_tools(tools_for_llm_local) if tools_for_llm_local else llm_base
            )
            tool_messages: list[ToolMessage]
            iterations = 0
            # Start from the decide-produced tool calls (if any), otherwise ask anew
            pending_calls = list(state.tool_calls)
            while iterations < 3:
                messages = _build_messages_for_session(session_id, state)
                if pending_calls:
                    # Reconstruct an AIMessage with tool_calls to pair tool results
                    out_msg = AIMessage(content=state.text or "", tool_calls=pending_calls)
                else:
                    out_msg = llm_with_tools.invoke(messages)
                    if not (isinstance(out_msg, AIMessage) and getattr(out_msg, "tool_calls", None)):
                        # No more tool calls; take answer
                        if isinstance(out_msg, AIMessage):
                            if out_msg.content and isinstance(out_msg.content, str):
                                state.text = out_msg.content
                            elif isinstance(out_msg.content, list):
                                list_text = [i['text'] for i in out_msg.content if i['type'] == 'text']
                                state.text = "\n".join(list_text)
                            else:
                                state.text = ""
                        else:
                            state.text = str(getattr(out_msg, "content", ""))
                        break

                tool_messages = []
                for call in getattr(out_msg, "tool_calls", []) or []:
                    try:
                        name = call.get('name')
                        args = call.get('args') or {}
                        registry_name = state.sanitized_to_original.get(name, name)
                        # Auto-augment agents.call payload with session context
                        if registry_name == "agents.call":
                            payload = dict(args.get("payload") or {})
                            # Build minimal convo_history for downstream agent
                            history_factory = get_session_history_factory(settings)
                            redis_history = history_factory(session_id)
                            hist_items: List[Dict[str, str]] = []
                            try:
                                for m in list(redis_history.messages):
                                    role = "assistant" if isinstance(m, AIMessage) else "user"
                                    hist_items.append({"role": role, "content": str(m.content)})
                            except Exception as e:  # noqa: BLE001
                                logger.exception("convo_history build failed: %s", e)
                            payload.setdefault("session_id", session_id)
                            if state.incoming_text:
                                payload.setdefault("user_message", state.incoming_text)
                            if hist_items:
                                payload.setdefault("convo_history", hist_items)
                            if not payload and (args.get("agent_id") or "") == "onboarder":
                                args["agent_id"] = "interviewer"
                                payload = {"kind": "onboarder", **payload}
                            elif (args.get("agent_id") or "") == "interviewer" and "kind" not in payload:
                                payload["kind"] = "onboarder"
                            args["payload"] = payload

                        # Ensure args are JSON-safe for downstream LLM serialization flows
                        args = _json_safe(args)
                        result = SENSITIVE_TOOLS.call(registry_name, args)
                        tool_messages.append(
                            ToolMessage(content=json.dumps(_json_safe(result)), tool_call_id=call.get("id", ""))
                        )
                    except Exception as e:  # noqa: BLE001
                        logger.exception("journaling tool exec failed: %s", e)
                        tool_messages.append(
                            ToolMessage(content=['ERROR', *e.args], tool_call_id=call.get("id", ""))
                        )

                tool_messages = [msg for msg in tool_messages if msg.content]
                messages_with_tools = messages + [out_msg, *tool_messages]
                out2 = llm_with_tools.invoke(messages_with_tools)
                iterations += 1
                if isinstance(out2, AIMessage) and getattr(out2, "tool_calls", None):
                    # Continue loop with new calls
                    pending_calls = [
                        {"id": c.get("id", ""), "name": c.get("name"), "args": c.get("args", {})}
                        for c in out2.tool_calls
                    ]
                    # Capture any draft text
                    if out2.content and isinstance(out2.content, str):
                        state.text = out2.content
                    continue
                else:
                    # Final answer from tool loop
                    if isinstance(out2, AIMessage):
                        if out2.content and isinstance(out2.content, str):
                            state.text = out2.content
                        elif isinstance(out2.content, list):
                            list_text = [i['text'] for i in out2.content if i['type'] == 'text']
                            state.text = "\n".join(list_text)
                        else:
                            state.text = ""
                    else:
                        state.text = str(getattr(out2, "content", ""))
                    break

            state.tool_iterations = iterations
            state.needs_tools = False
            return state

        def node_finalize_short(state: AgentState) -> AgentState:
            # Add a short system directive to produce a concise, user-facing answer
            session_id = str(state.session_id or "").strip()
            llm_base = llm.bind(reasoning={"effort": "high"})
            messages = _build_messages_for_session(session_id, state)
            finalizer = SystemMessage(
                content=(
                    "Provide a concise, empathetic response based on the tool results and context. "
                    "Do not mention internal tools."
                )
            )
            # Include the current draft answer so the model can refine it
            out = llm_base.invoke(messages + [finalizer, AIMessage(content=state.text or "")])
            if isinstance(out, AIMessage):
                if out.content and isinstance(out.content, str):
                    state.text = out.content
                elif isinstance(out.content, list):
                    list_text = [i['text'] for i in out.content if i['type'] == 'text']
                    state.text = "\n".join(list_text)
                else:
                    state.text = state.text
            return state

        def node_send_and_persist(state: AgentState) -> AgentState:
            # Send to DRF gateway if telegram
            session_id = str(state.session_id or "").strip()
            if session_id.startswith("telegram:"):
                try:
                    chat_id = session_id.split(":")[1]
                    celery_app.send_task(
                        "recieved.telegram",
                        args=[chat_id, state.text],
                        queue="gateway",
                    )
                except Exception as e:  # noqa: BLE001
                    logger.exception("gateway send failed: %s", e)

            # Persist assistant message
            history_factory = get_session_history_factory(settings)
            redis_history = history_factory(session_id)
            try:
                if state.text:
                    redis_history.add_ai_message(state.text)
            except Exception as e:  # noqa: BLE001
                logger.exception("history write failed: %s", e)

            # Vector memory writes
            try:
                if len(state.incoming_text or "") > 200:
                    memory.vectorstore.add_texts(
                        [state.incoming_text],
                        metadatas=[
                            {"agent": "journaling", "role": "user", "session_id": session_id},
                        ],
                    )
            except Exception as e:  # noqa: BLE001
                logger.exception("write memory failed: %s", e)
            try:
                if len(state.text or "") > 200:
                    memory.vectorstore.add_texts(
                        [state.text],
                        metadatas=[
                            {"agent": "journaling", "role": "assistant", "session_id": session_id},
                        ],
                    )
            except Exception as e:  # noqa: BLE001
                logger.exception("write memory failed: %s", e)

            # Mirror text into assistant for upstream callers
            return state.model_copy(update={"assistant": state.text})

        graph = StateGraph(AgentState)
        graph.add_node("decide", node_decide)
        graph.add_node("answer_direct", node_answer_direct)
        graph.add_node("tool_loop", node_tool_loop)
        graph.add_node("finalize_short", node_finalize_short)
        graph.add_node("send_and_persist", node_send_and_persist)

        graph.set_entry_point("decide")

        def branch(state: AgentState) -> bool:
            return bool(state.needs_tools)

        graph.add_conditional_edges(
            "decide",
            branch,
            {True: "tool_loop", False: "answer_direct"},
        )
        graph.add_edge("answer_direct", "send_and_persist")
        graph.add_edge("tool_loop", "finalize_short")
        graph.add_edge("finalize_short", "send_and_persist")
        graph.add_edge("send_and_persist", END)
        return graph


JournalingFlow()()
