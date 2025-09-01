"""Journaling WebSocket consumer.

Ephemeral chat: opens a run with the public journaling agent and streams messages
over RabbitMQ to this socket. No persistence.
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Dict

from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from celery import current_app as celery_app
from kombu import Connection, Exchange, Queue

from .utils import BaseConsumer


class JournalConsumer(BaseConsumer):
    """WebSocket for ephemeral journaling sessions.

    Path: /ws/journal/<str:session_id>
    """

    agent_name = "journaling"

    manifest = {
            "agent_ids": ["journaling"],
            "tool_ids": [],
            "memory_namespaces": [],
            "queue": "sensitive",
        }

    async def journaling_message(self, event: Dict[str, Any]) -> None:  # type: ignore[override]
        await self.send(json.dumps(event))

    async def disconnect(self, close_code: int) -> None:
        await self.send(json.dumps({"type": "message", "disconnect": True}))
        await super().disconnect(close_code)