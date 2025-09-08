from __future__ import annotations
import json
from typing import Optional
from pydantic import BaseModel
from langgraph.graph import END, StateGraph
from langchain_core.language_models.chat_models import BaseChatModel

from athena_langchain.agents.prompts.guardian import appeals_prompt as prompt
from athena_langchain.config import Settings
from athena_langchain.agents.registry import REGISTRY
from athena_langchain.agents.utils import BaseFlow
from athena_langchain.tools.policies.schedule import (
    get_current_strictness,
    get_current_goal,
)


class AppealState(BaseModel, frozen=False):
    session_id: Optional[str] = None
    # App/site context
    url: str = ""
    title: str = ""
    host: str = ""
    path: str = ""
    package: str = ""
    activity: str = ""
    # User appeal content
    user_justification: str = ""
    requested_minutes: int = 0
    # Outputs
    assistant: str = ""
    allow: bool = False
    minutes: int = 0


class AppealsFlow(BaseFlow):
    registry = REGISTRY
    name = "appeals"
    description = (
        "Evaluate user appeals using strictness and current goal; "
        "returns allow + minutes."
    )
    model_name = "gpt-5"
    temperature = 0.0

    def build_graph(self, settings: Settings, llm: BaseChatModel) -> StateGraph:

        def evaluate(state: AppealState) -> AppealState:
            strict = get_current_strictness(
                settings,
                session_id=state.session_id,
            )
            goal = get_current_goal(
                settings,
                session_id=state.session_id,
            )
            chain = prompt | llm
            out = chain.invoke({
                **state.model_dump(include={
                    "user_justification",
                    "requested_minutes",
                    "host",
                    "path",
                    "title",
                    "package",
                    "activity",
                }),
                "strictness": strict,
                "goal": goal,
            })

            data = json.loads(out.content)

            updated = state.model_copy(update={
                "assistant": str(data.get("assistant", "")),
                "allow": bool(data.get("allow", False)),
                "minutes": int(data.get("minutes", 0)),
            })
            # Clamp minutes 0..15
            minutes = updated.minutes
            if minutes < 0:
                minutes = 0
            if minutes > 15:
                minutes = 15
            return updated.model_copy(update={"minutes": minutes})

        graph = StateGraph(AppealState)
        graph.add_node("evaluate", evaluate)
        graph.set_entry_point("evaluate")
        graph.add_edge("evaluate", END)
        return graph


AppealsFlow()()
