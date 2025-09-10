"""Appeals WebSocket consumer.

Moved from `api/consumers.py` to keep consumers organized by feature.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from .utils import BaseConsumer


class AppealsConsumer(BaseConsumer):
    """WebSocket for appeals mediation per event_id.

    Path: /ws/appeals/<str:event_id>
    """

    agent_name = "appeals"

    # Base manifest for appeals runs; metadata is injected in BaseConsumer
    manifest = {
        "agent_ids": ["appeals"],
        "tool_ids": [],
        "memory_namespaces": [],
        "queue": "sensitive",
    }

    async def connect(self) -> None:
        await super().connect()
        await self._start_agent_run({"text": ""})

    async def appeals_message(self, event: Dict[str, Any]) -> None:  # type: ignore[override]
        await self.send(json.dumps({"type": "message", "data": event.get("data", {})}))


