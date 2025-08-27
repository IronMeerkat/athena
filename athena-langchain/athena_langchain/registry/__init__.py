"""
Registries for segregating public and sensitive agents/tools.
"""

from __future__ import annotations

from .agents_base import AgentRegistry, AgentEntry, AgentConfig  # noqa: F401

# Two separate registries for agents
PUBLIC_AGENTS = AgentRegistry()
SENSITIVE_AGENTS = AgentRegistry()

__all__ = [
    "AgentRegistry",
    "AgentEntry",
    "AgentConfig",
    "PUBLIC_AGENTS",
    "SENSITIVE_AGENTS",
]