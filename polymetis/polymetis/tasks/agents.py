from __future__ import annotations

from typing import Dict

from celery import shared_task

from ..registry import PUBLIC_AGENTS, SENSITIVE_AGENTS


def _serialize_agents(registry) -> Dict[str, dict]:
    # Convert AgentConfig dataclasses to plain dicts
    out: Dict[str, dict] = {}
    for agent_id, cfg in registry.list().items():
        out[agent_id] = {
            "name": cfg.name,
            "description": cfg.description,
            "model_name": cfg.model_name,
            "llm_provider": getattr(cfg, "llm_provider", None),
            "temperature": getattr(cfg, "temperature", None),
        }
    return out


@shared_task(name="agents.list_public")
def list_public_agents() -> Dict[str, dict]:
    return _serialize_agents(PUBLIC_AGENTS)


@shared_task(name="agents.list_sensitive")
def list_sensitive_agents() -> Dict[str, dict]:
    return _serialize_agents(SENSITIVE_AGENTS)


