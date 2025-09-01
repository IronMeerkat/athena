from __future__ import annotations

import json
import threading
import time
from typing import Any, Dict

from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from celery import current_app as celery_app
from kombu import Connection, Exchange, Queue


class BaseConsumer(AsyncWebsocketConsumer):
    """Base WebSocket consumer for all consumers."""

    async def connect(self) -> None:
        self.session_id = self.scope["url_route"]["kwargs"].get("session_id")
        self.group_name = f"{self.agent_name}.{self.session_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Start RMQ listener thread for this session's events
        self._stop = False
        self._listener = threading.Thread(target=self._listen_rmq, daemon=True)
        self._listener.start()

    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None) -> None:
        if text_data is None:
            return
        try:
            data = json.loads(text_data)
        except Exception:
            data = {"text": text_data}
        await self._start_agent_run(data)

    async def disconnect(self, close_code: int) -> None:
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        try:
            self._stop = True
            self._listener.join(timeout=0.2)
        except Exception:
            pass

    async def _start_agent_run(self, payload: Dict[str, Any]) -> None:

        manifest = {**self.manifest,
                    "metadata": {'session_id': self.session_id}
                    }

        celery_app.send_task(
            "runs.execute_graph",
            args=[self.session_id, self.agent_name, payload, manifest],
            queue="sensitive",
        )

    # Background RMQ listener: forwards worker events to the socket group
    def _listen_rmq(self) -> None:
        broker_url = settings.CELERY_BROKER_URL
        exchange = Exchange("runs", type="topic")
        queue_name = f"{self.agent_name}.ws.{self.session_id}"
        routing_key = f"runs.{self.session_id}"
        try:
            with Connection(broker_url) as conn:
                q = Queue(queue_name, exchange=exchange, routing_key=routing_key, durable=False, auto_delete=True)
                with conn.channel() as channel:
                    bq = q(channel)
                    bq.declare()
                    while not getattr(self, "_stop", False):
                        msg = bq.get(no_ack=True)
                        if not msg:
                            time.sleep(0.2)
                            continue
                        payload = msg.payload or {}
                        event_type = payload.get("event")
                        data = payload.get("data", {})
                        text = None
                        if isinstance(data, dict):
                            text = data.get("assistant") or data.get("text") or data.get("message")
                        if text:
                            data = {"text": text}
                        from asgiref.sync import async_to_sync
                        async_to_sync(self.channel_layer.group_send)(
                            self.group_name,
                            {"type": f"{self.agent_name}.message", "data": data},
                        )
        except Exception:
            return


