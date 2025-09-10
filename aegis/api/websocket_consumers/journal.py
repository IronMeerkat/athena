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
from channels.db import database_sync_to_async

from .utils import BaseConsumer
from api.models import Chat, ChatMessage
from django.utils import timezone


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
        # Persist history snapshot if received and forward to client
        data = event.get("data", {})
        snapshot = data.get("history_snapshot") if isinstance(data, dict) else None
        if snapshot and isinstance(snapshot, dict):
            try:
                await database_sync_to_async(self._persist_history_snapshot)(snapshot)
            except Exception:
                pass
        await self.send(json.dumps(event))

    async def connect(self) -> None:
        await super().connect()
        # Load chat history from Postgres and notify agent
        history = await database_sync_to_async(self._load_or_create_history)()
        await self._start_agent_run({
            "connect": True,
            "convo_history": history,
        })
        # Send initial history to Android client as well
        await self.send(json.dumps({
            "type": "message",
            "data": {"history_snapshot": {"messages": history}},
        }))
        await self.send(json.dumps({"type": "message", "connect": True}))

    async def disconnect(self, close_code: int) -> None:
        # Request the agent to emit a final history snapshot
        try:
            await self._start_agent_run({"disconnect": True})
        except Exception:
            pass
        await self.send(json.dumps({"type": "message", "disconnect": True}))
        await super().disconnect(close_code)

    # Persist user messages when received from client
    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None) -> None:
        if text_data:
            try:
                data = json.loads(text_data)
            except Exception:
                data = {"text": text_data}
            text = (data.get("user_message") or data.get("text") or "").strip()
            if text:
                try:
                    await database_sync_to_async(self._persist_message)(role=ChatMessage.ROLE_USER, content=text)
                except Exception:
                    pass
        await super().receive(text_data=text_data, bytes_data=bytes_data)

    # Hook called from BaseConsumer background thread when agent responds
    def on_agent_message(self, text: str) -> None:
        try:
            self._persist_message(role=ChatMessage.ROLE_ASSISTANT, content=text)
        except Exception:
            pass

    def _load_or_create_history(self) -> list[dict[str, str]]:
        # Get or create a Chat for this session
        chat, _ = Chat.objects.get_or_create(id=self.session_id, defaults={
            "user": getattr(self.scope.get("user"), "id", None) and self.scope.get("user") or None,
        })
        messages = list(chat.messages.order_by("created_at", "id"))
        history: list[dict[str, str]] = []
        for m in messages:
            role = "user" if m.role == ChatMessage.ROLE_USER else "assistant"
            history.append({"role": role, "content": m.content})
        return history

    def _persist_message(self, role: str, content: str) -> None:
        chat, _ = Chat.objects.get_or_create(id=self.session_id, defaults={
            "user": getattr(self.scope.get("user"), "id", None) and self.scope.get("user") or None,
        })
        ChatMessage.objects.create(chat=chat, role=role, content=content)
        # Touch updated_at on the chat
        Chat.objects.filter(id=chat.id).update(updated_at=timezone.now())

    def _persist_history_snapshot(self, snapshot: Dict[str, Any]) -> None:
        messages = snapshot.get("messages") or []
        if not isinstance(messages, list):
            return
        chat, _ = Chat.objects.get_or_create(id=self.session_id, defaults={
            "user": getattr(self.scope.get("user"), "id", None) and self.scope.get("user") or None,
        })
        for item in messages:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "user")
            content = str(item.get("content") or "").strip()
            if not content:
                continue
            if role not in (ChatMessage.ROLE_USER, ChatMessage.ROLE_ASSISTANT):
                role = ChatMessage.ROLE_USER if role != ChatMessage.ROLE_ASSISTANT else ChatMessage.ROLE_ASSISTANT
            ChatMessage.objects.create(chat=chat, role=role, content=content)
        Chat.objects.filter(id=chat.id).update(updated_at=timezone.now())