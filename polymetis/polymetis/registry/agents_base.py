from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional

from langgraph.graph import StateGraph
from langchain_core.language_models import BaseChatModel

from polymetis.config import Settings, make_llm
from polymetis.memory.vectorstore import MemoryDeps


@dataclass
class AgentConfig:
    name: str
    description: str
    # Per-agent LLM overrides
    model_name: Optional[str] = None  # override Settings.llm_model
    llm_provider: Optional[str] = None  # override Settings.llm_provider
    temperature: Optional[float] = None  # LLM temperature per agent


@dataclass
class AgentEntry:
    config: AgentConfig
    build_graph: Callable[[Settings, BaseChatModel, MemoryDeps], StateGraph]


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
        cfg = entry.config
        return make_llm(
            settings,
            provider=cfg.llm_provider,
            model=cfg.model_name,
            temperature=cfg.temperature,
        )


