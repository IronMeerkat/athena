from __future__ import annotations

import json
from typing import List
from pydantic import BaseModel

from langgraph.graph import END, StateGraph
from langchain_core.language_models.chat_models import BaseChatModel

from athena_langchain.config import Settings
from athena_langchain.agents.registry import REGISTRY
from athena_langchain.agents.utils import BaseFlow
from athena_langchain.tools.policies.schedule import save_schedule
from athena_langchain.memory.chat_history import get_session_history_factory
from athena_langchain.agents.prompts.goals import goals_prompt as prompt


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
        self, settings: Settings, llm: BaseChatModel
    ) -> StateGraph:

        def converse(state: AgentState) -> AgentState:
            chain = prompt | llm
            # Pull short chat history for memory
            session_id = state.session_id or "default"
            hist_factory = get_session_history_factory(settings)
            history = hist_factory(session_id)
            hist_msgs = history.messages[-10:]
            history_str = "\n".join(
                [f"{m.type}: {getattr(m, 'content', '')}" for m in hist_msgs]
            )
            out = chain.invoke({
                "history": history_str,
                "user_message": state.user_message,
            })

            data = json.loads(out.content)

            assistant = data["assistant"]
            schedule = data["schedule"]

            # Persist schedule
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
