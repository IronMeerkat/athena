from __future__ import annotations

from typing import Dict, List, Any
from pydantic import BaseModel, Field

from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage, SystemMessage

from athena_langchain.config import Settings
from athena_langchain.registry import SENSITIVE_AGENTS as REGISTRY
from athena_langchain.agents.utils import BaseFlow
from athena_langchain.memory.chat_history import (
    get_session_history_factory,
)
from athena_langchain.tools.merged_tools import to_openai_function_specs
from athena_langchain.celery import app as celery_app
from athena_langchain.memory.vectorstore import MemoryDeps
from athena_logging import get_logger
from athena_langchain.agents.utils import _json_safe
from athena_langchain.tools.merged_tools import get_merged_tools_sync
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
    messages: List[BaseMessage] = Field(default_factory=list)
    messages_snapshot: List[BaseMessage] = Field(default_factory=list)
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

        def node_prepare(state: AgentState) -> AgentState:
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

            # Build initial messages for model
            messages = prompt.format_messages(
                user_message=incoming_text,
                history=lc_history,
                context=context_text,
            )
            state.messages = messages
            return state

        def node_call_model(state: AgentState) -> Dict[str, Any]:
            tools = get_merged_tools_sync()
            # Bind dict specs to the model to avoid BaseTool subset conversion issues

            tool_specs = to_openai_function_specs(tools)
            llm_base = llm.bind(reasoning={"effort": "high"})
            model = llm_base.bind_tools(tool_specs) if tool_specs else llm_base
            try:
                response = model.invoke(state.messages)
            except Exception as e:  # noqa: BLE001
                logger.exception("model invoke failed: %s", e)
                return {"messages": state.messages}
            # Append response to messages and snapshot pre-tool state for merging later
            msgs = list(state.messages) + ([response] if response is not None else [])
            return {"messages": msgs, "messages_snapshot": msgs}

        def node_finalize_short(state: AgentState) -> AgentState:
            # Extract final assistant message from conversation
            text = state.text or ""
            try:
                for m in reversed(state.messages or []):
                    if isinstance(m, AIMessage) and getattr(m, "content", None):
                        if isinstance(m.content, str):
                            text = m.content
                            break
                        if isinstance(m.content, list):
                            list_text = [i.get('text') for i in m.content if isinstance(i, dict) and i.get('type') == 'text']
                            text = "\n".join([t for t in list_text if isinstance(t, str)])
                            break
            except Exception as e:  # noqa: BLE001
                logger.exception("finalize failed: %s", e)
            if not text:
                text = ""
            state.text = text
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
        graph.add_node("prepare", node_prepare)
        graph.add_node("call_model", node_call_model)
        graph.add_node(ToolNode(get_merged_tools_sync()))  # registers a node named "tools"

        def node_merge_tool_messages(state: AgentState) -> AgentState:
            try:
                prev = list(state.messages_snapshot or [])
                cur = list(state.messages or [])
                # If cur starts with tool messages, prepend previous convo
                merged = prev + cur
                state.messages = merged
            except Exception as e:  # noqa: BLE001
                logger.exception("merge tool messages failed: %s", e)
            return state

        graph.add_node("merge_tool_messages", node_merge_tool_messages)
        graph.add_node("finalize_short", node_finalize_short)
        graph.add_node("send_and_persist", node_send_and_persist)

        graph.set_entry_point("prepare")

        def needs_model(state: AgentState) -> bool:
            # If prepare produced a direct assistant or snapshot, skip model
            return not (bool(state.assistant) or bool(state.history_snapshot))

        graph.add_conditional_edges(
            "prepare",
            needs_model,
            {True: "call_model", False: "send_and_persist"},
        )

        def has_tool_calls(state: AgentState) -> bool:
            try:
                last = (state.messages or [])[-1]
                return isinstance(last, AIMessage) and bool(getattr(last, "tool_calls", None))
            except Exception:
                return False

        graph.add_conditional_edges(
            "call_model",
            has_tool_calls,
            {True: "tools", False: "finalize_short"},
        )
        graph.add_edge("tools", "merge_tool_messages")
        graph.add_edge("merge_tool_messages", "call_model")
        graph.add_edge("finalize_short", "send_and_persist")
        graph.add_edge("send_and_persist", END)
        return graph


JournalingFlow()()
