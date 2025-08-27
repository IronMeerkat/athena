from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional

from langgraph.graph import StateGraph
from langchain_core.language_models import BaseChatModel

from athena_langchain.config import Settings, make_llm


@dataclass
class AgentConfig:
    name: str
    description: str
    model_name: Optional[str] = None  # override Settings.llm_model


@dataclass
class AgentEntry:
    config: AgentConfig
    build_graph: Callable[[Settings, BaseChatModel], StateGraph]


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: Dict[str, AgentEntry] = {}

    def register(self, agent_id: str, entry: AgentEntry) -> None:
        if agent_id in self._agents:
            raise ValueError(f"Agent already registered: {agent_id}")
        self._agents[agent_id] = entry

    def get(self, agent_id: str) -> AgentEntry:
        if agent_id not in self._agents:
            raise KeyError(f"Unknown agent: {agent_id}")
        return self._agents[agent_id]

    def list(self) -> Dict[str, AgentConfig]:
        return {k: v.config for k, v in self._agents.items()}

    def build_llm(self, settings: Settings, agent_id: str) -> BaseChatModel:
        entry = self.get(agent_id)
        if entry.config.model_name:
            # Create a temporary settings object with overridden model
            tmp = Settings(**settings.model_dump())
            tmp.llm_model = entry.config.model_name
            return make_llm(tmp)
        return make_llm(settings)


