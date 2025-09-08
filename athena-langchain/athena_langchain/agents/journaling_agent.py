from __future__ import annotations

from typing import Dict, List
from pydantic import BaseModel

from langgraph.graph import END, StateGraph
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from athena_langchain.config import Settings
from athena_langchain.registry import SENSITIVE_AGENTS as REGISTRY
from athena_langchain.agents.utils import BaseFlow
from athena_langchain.memory.chat_history import (
    get_session_history_factory,
)
from athena_langchain.celery import app as celery_app

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AgentState(BaseModel, frozen=False):
    user_message: str = ""
    text: str = ""
    assistant: str = ""
    connect: bool = False
    disconnect: bool = False
    convo_history: List[Dict[str, str]] = []
    session_id: str = ""


class JournalingFlow(BaseFlow):
    registry = REGISTRY
    name = "journaling"
    description = (
        "A lightweight journaling companion that reflects and asks questions."
    )
    model_name = "gpt-5-mini"
    temperature = 0.8

    def build_graph(
        self, settings: Settings, llm: BaseChatModel
    ) -> StateGraph:
        from athena_langchain.agents.prompts.journaling import (
            journaling_prompt as prompt,
        )

        def converse(state: AgentState) -> AgentState:
            # Normalize DRF-style payloads: accept either
            # "user_message" or "text"
            incoming_text = str(
                state.user_message or state.text or ""
            ).strip()
            session_id = str(state.session_id or "").strip()
            history_factory = get_session_history_factory(settings)
            redis_history = history_factory(session_id)

            def respond(next_state: AgentState) -> AgentState:
                if session_id.startswith("telegram:"):
                    chat_id = session_id.split(":")[1]
                    # Route to DRF worker gateway so DRF persists+relays
                    celery_app.send_task(
                        "recieved.telegram",
                        args=[chat_id, next_state.assistant],
                        queue="gateway",
                    )
                return next_state

            def to_lc_messages(
                items: List[Dict[str, str]]
            ) -> List[BaseMessage]:
                messages: List[BaseMessage] = []
                for item in items:
                    role = (item.get("role") or "").lower()
                    content = (
                        item.get("content") or item.get("text") or ""
                    )
                    if not content:
                        continue
                    if role == "assistant":
                        messages.append(AIMessage(content=content))
                    else:
                        messages.append(HumanMessage(content=content))
                return messages

            if state.connect:
                convo_history = state.convo_history
                logger.info("connect: %s", state.connect)
                if convo_history:
                    redis_history.clear()
                    for message in to_lc_messages(convo_history):
                        redis_history.add_message(message)

            # If chat is new, send the first message
            if not redis_history.messages or incoming_text == "/start":
                first = "Hi, I'm Athena. What's on your mind today?"
                if redis_history is not None:
                    redis_history.add_ai_message(first)
                return respond(state.model_copy(update={"assistant": first}))

            if state.disconnect:
                logger.info("disconnect: %s", state.disconnect)
                # Send the full history back (for DRF to persist/confirm)
                hist_items: List[Dict[str, str]] = []
                for m in redis_history.messages:
                    role = "assistant" if isinstance(m, AIMessage) else "user"
                    hist_items.append(
                        {"role": role, "content": str(m.content)}
                    )
                return respond(
                    state.model_copy(
                        update={
                            "history_snapshot": {"messages": hist_items}
                        }
                    )
                )

            # No-op on empty input: return ack by leaving assistant empty
            if not incoming_text:
                return respond(
                    state.model_copy(update={"assistant": ""})
                )

            # Build LC history for context
            lc_history: List[BaseMessage] = []
            try:
                if redis_history is not None:
                    # Append incoming user message prior to generation
                    redis_history.add_user_message(incoming_text)
                    lc_history = list(redis_history.messages)
            except Exception as e:
                logger.exception("history fallback error: %s", e)
                lc_history = to_lc_messages(state.convo_history or [])

            chain = prompt | llm
            out = chain.invoke({
                "user_message": incoming_text,
                "history": lc_history,
            })

            logger.info("content: %s", out.content)
            text = (
                out.content if isinstance(out.content, str) else str(out)
            ).strip()
            redis_history.add_ai_message(text)
            return respond(state.model_copy(update={"assistant": text}))

        graph = StateGraph(AgentState)
        graph.add_node("converse", converse)
        graph.set_entry_point("converse")
        graph.add_edge("converse", END)
        return graph


JournalingFlow()()
