"""
Sensitive agent and tool registry.

This module defines agents and tools that are available only to the
sensitive worker.  These agents may require elevated privileges or
access to secrets and should never be executed by the public worker.
"""

from __future__ import annotations

from typing import Dict

AGENTS: Dict[str, object] = {}