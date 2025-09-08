from athena_langchain.celery import app as celery_app
from athena_langchain.config import Settings
from athena_langchain.registry.agents_base import (
    AgentRegistry,
    AgentEntry,
    AgentConfig,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import StateGraph
from typing import TypedDict, TypeVar

T = TypeVar('T', bound=TypedDict)


class BaseFlow:

    settings: Settings
    registry: AgentRegistry
    name: str
    description: str
    model_name: str
    temperature: float
    llm: BaseChatModel

    def build_graph(
        self, settings: Settings, llm: BaseChatModel
    ) -> StateGraph:
        raise NotImplementedError(
            "Subclasses must implement build_graph"
        )

    def __call__(self) -> None:
        self.registry.register(
            self.name,
            AgentEntry(
                config=AgentConfig(
                    name=self.name,
                    description=self.description,
                    model_name=self.model_name,
                    temperature=self.temperature,
                ),
                build_graph=self.build_graph,
            ),
        )


def message_drf(name: str, state: T) -> T:
    celery_app.send_task(
        name,
        args=[state],
        queue="gateway",
    )
    return state
