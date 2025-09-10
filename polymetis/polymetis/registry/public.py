"""
Public agent and tool registry.

This module defines a dictionary of agent identifiers to callable
constructors or graph objects that are safe to run in the public worker.
Only non‑sensitive agents and tools should be listed here.  The
registries are intentionally small in this boilerplate; add your own
entries as you build out your application.
"""

from __future__ import annotations

from typing import Dict

# A mapping from agent ID to a factory function or callable that returns
# the agent or graph implementation.  For a boilerplate, we leave this
# empty; you should populate it with your public agents.
AGENTS: Dict[str, object] = {}