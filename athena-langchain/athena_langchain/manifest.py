"""
Capability manifest for Athena workers.

This module defines a simple data class used to represent the
permissions and limits granted to a particular run.  The DRF gateway
constructs a manifest for each incoming request based on the user's
role and the requested agent/tool; the manifest is then passed to the
LangChain worker to enforce hard boundaries on what the agent can do.

The fields here mirror those described in the design discussion: which
agents/tools/memory namespaces are allowed, which queue to route the
task to, and various resource limits.  You can extend this class with
additional fields (e.g. rate limits, timeouts) as your needs grow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class CapabilityManifest:
    """A manifest describing the permissions and limits for a run."""

    agent_ids: List[str]
    tool_ids: List[str]
    memory_namespaces: List[str]
    queue: str
    max_tokens: int
    max_cost_cents: int
    expires_at: Optional[datetime] = None
    # Additional arbitrary metadata can be included for auditing or
    # validation purposes.  This field is ignored by the runner unless
    # explicitly checked.
    metadata: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "CapabilityManifest":
        """Deserialize a CapabilityManifest from a plain Python dict."""
        expires_at_val = data.get("expires_at")
        if isinstance(expires_at_val, str):
            try:
                expires_at = datetime.fromisoformat(expires_at_val)
            except ValueError:
                expires_at = None
        else:
            expires_at = None
        return cls(
            agent_ids=list(data.get("agent_ids", [])),
            tool_ids=list(data.get("tool_ids", [])),
            memory_namespaces=list(data.get("memory_namespaces", [])),
            queue=str(data.get("queue", "public")),
            max_tokens=int(data.get("max_tokens", 0)),
            max_cost_cents=int(data.get("max_cost_cents", 0)),
            expires_at=expires_at,
            metadata=dict(data.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, object]:
        """Serialize this manifest to a JSON‑compatible dict."""
        return {
            "agent_ids": self.agent_ids,
            "tool_ids": self.tool_ids,
            "memory_namespaces": self.memory_namespaces,
            "queue": self.queue,
            "max_tokens": self.max_tokens,
            "max_cost_cents": self.max_cost_cents,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata,
        }