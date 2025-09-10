from __future__ import annotations

import json
from typing import Dict, List
from pydantic import BaseModel

from langgraph.graph import END, StateGraph
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from athena_langchain.config import Settings
from athena_langchain.registry import SENSITIVE_AGENTS as REGISTRY
from athena_langchain.agents.utils import BaseFlow
from athena_langchain.memory.chat_history import (
    get_session_history_factory,
)
from athena_langchain.memory.vectorstore import MemoryDeps
from athena_logging import get_logger


logger = get_logger(__name__)


class InterviewerState(BaseModel, frozen=False):
    user_message: str = ""
    text: str = ""
    assistant: str = ""
    convo_history: List[Dict[str, str]] = []
    session_id: str = ""
    kind: str = ""  # "onboarder" for initial onboarding; domain kinds for periodic check-ins


class InterviewerFlow(BaseFlow):
    registry = REGISTRY
    name = "interviewer"
    description = (
        "Generate onboarding or periodic check-in questions to personalize Athena."
    )
    model_name = "gpt-5"
    temperature = 0.5

    def build_graph(
        self, settings: Settings, llm: BaseChatModel, memory: MemoryDeps
    ) -> StateGraph:
        from athena_langchain.agents.prompts.onboarder import (
            onboarder_prompt,
        )
        from athena_langchain.agents.prompts.interviewer import (
            get_interviewer_prompt,
        )

        def to_lc_messages(items: List[Dict[str, str]]) -> List[BaseMessage]:
            messages: List[BaseMessage] = []
            for item in items:
                role = (item.get("role") or "").lower()
                content = item.get("content") or item.get("text") or ""
                if not content:
                    continue
                if role == "assistant":
                    messages.append(AIMessage(content=content))
                else:
                    messages.append(HumanMessage(content=content))
            return messages

        def run(state: InterviewerState) -> InterviewerState:
            user_message = str(state.user_message or state.text or "").strip()
            session_id = str(state.session_id or "").strip()
            kind = (state.kind or "").strip().lower() or "onboarder"

            history_factory = get_session_history_factory(settings)
            redis_history = history_factory(session_id)

            # Build LC history for context
            lc_history: List[BaseMessage] = []
            try:
                if redis_history is not None:
                    lc_history = list(redis_history.messages)
            except Exception as e:  # noqa: BLE001
                logger.exception("interviewer history error: %s", e)
                lc_history = to_lc_messages(state.convo_history or [])

            # Retrieve tiny context based on recent content
            try:
                query = user_message or ("periodic " + kind)
                docs = memory.retriever.invoke(query) if query else []
                context = "\n\n".join([d.page_content for d in docs]) if docs else ""
            except Exception as e:  # noqa: BLE001
                logger.exception("interviewer retrieval failed: %s", e)
                context = ""

            # Select prompt
            try:
                prompt = (
                    onboarder_prompt if kind == "onboarder" else get_interviewer_prompt(kind)
                )
            except Exception as e:  # noqa: BLE001
                logger.exception("unknown interviewer kind '%s': %s", kind, e)
                prompt = onboarder_prompt

            messages = prompt.format_messages(
                user_message=user_message,
                history=lc_history,
                context=context,
            )
            # Ensure high reasoning effort for this agent
            llm_with_reasoning = llm.bind(reasoning={"effort": "high"})
            out = llm_with_reasoning.invoke(messages)

            try:
                content = out.content if isinstance(out.content, str) else str(out)
                data = json.loads(content)
            except Exception:
                content = out.content if isinstance(out.content, str) else str(out)
                data = {"questions": [content.strip()] if content.strip() else []}

            text = json.dumps(data)
            if redis_history is not None and text:
                try:
                    redis_history.add_ai_message(text)
                except Exception as e:  # noqa: BLE001
                    logger.exception("interviewer write history failed: %s", e)

            return state.model_copy(update={"assistant": text})

        graph = StateGraph(InterviewerState)
        graph.add_node("run", run)
        graph.set_entry_point("run")
        graph.add_edge("run", END)
        return graph


InterviewerFlow()()


