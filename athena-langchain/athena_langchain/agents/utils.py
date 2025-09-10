from athena_langchain.celery import app as celery_app
from athena_langchain.config import Settings
from athena_langchain.registry.agents_base import (
    AgentRegistry,
    AgentEntry,
    AgentConfig,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import StateGraph
from athena_langchain.memory.vectorstore import MemoryDeps
from typing import TypedDict, TypeVar, Any
from bson import ObjectId, Decimal128
from bson.binary import Binary
from datetime import datetime
import base64
from athena_logging import get_logger
logger = get_logger(__name__)

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
        self, settings: Settings, llm: BaseChatModel, memory: MemoryDeps
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


def _json_safe(value: Any) -> Any:
    try:
        if isinstance(value, ObjectId):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Decimal128):
            return str(value)
        if isinstance(value, Binary):
            return base64.b64encode(bytes(value)).decode("ascii")
        if isinstance(value, dict):
            return {k: _json_safe(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_json_safe(v) for v in value]
    except Exception as e:  # noqa: BLE001
        logger.warning(f"json_safe conversion failed: value {value} of type {type(value)}")
    return value