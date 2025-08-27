"""
WebSocket consumers for the API app.

This module defines WebSocket consumers used by the Athena gateway.  The
``EchoConsumer`` provided here simply echoes any incoming text message
back to the client and is intended only for demonstration purposes.
Replace or extend this consumer with your own real‑time functionality.
"""

from channels.generic.websocket import AsyncWebsocketConsumer
from typing import Any, Dict
import json
import threading
import time
from django.conf import settings
from celery import current_app as celery_app
from kombu import Connection, Exchange, Queue


class AppealsConsumer(AsyncWebsocketConsumer):
    """WebSocket for appeals mediation per event_id.

    Path: /ws/appeals/{event_id}
    """

    async def connect(self) -> None:
        self.event_id = self.scope["url_route"]["kwargs"].get("event_id")  # type: ignore[assignment]
        self.group_name = f"appeals.{self.event_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        # Start RMQ listener thread for appeal outcomes
        self._stop = False  # type: ignore[attr-defined]
        self._listener = threading.Thread(target=self._listen_rmq, daemon=True)  # type: ignore[attr-defined]
        self._listener.start()

    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None) -> None:
        if not text_data:
            return
        try:
            data: Dict[str, Any] = json.loads(text_data)
        except Exception:
            await self.send(json.dumps({"type": "error", "message": "invalid json"}))
            return
        # If client initiates an appeal, enqueue to worker using same run_id (event_id)
        if data.get("type") == "appeal":
            payload = {
                "event_id": self.event_id,
                "user_justification": data.get("user_justification", ""),
                "requested_minutes": int(data.get("requested_minutes", 0)),
            }
            manifest = {
                "agent_ids": ["appeals"],
                "tool_ids": [],
                "memory_namespaces": [],
                "queue": "sensitive",
                "max_tokens": 2000,
                "max_cost_cents": 10,
                "metadata": {"event_id": self.event_id},
            }
            try:
                celery_app.send_task(
                    "runs.execute_graph",
                    args=[self.event_id, "appeals", payload, manifest],
                    queue="sensitive",
                )
                await self.send(json.dumps({"type": "accepted"}))
            except Exception as e:  # noqa: BLE001
                await self.send(json.dumps({"type": "error", "message": str(e)}))
        else:
            # Echo to group for broadcast/testing
            await self.channel_layer.group_send(self.group_name, {"type": "appeals.message", "data": data})

    async def appeals_message(self, event: Dict[str, Any]) -> None:  # type: ignore[override]
        await self.send(json.dumps({"type": "event", "data": event.get("data", {})}))

    async def disconnect(self, close_code: int) -> None:
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        # Stop listener
        try:
            self._stop = True  # type: ignore[attr-defined]
            if getattr(self, "_listener", None):  # type: ignore[attr-defined]
                self._listener.join(timeout=0.2)  # type: ignore[attr-defined]
        except Exception:
            pass

    # Internal: run in a background thread
    def _listen_rmq(self) -> None:
        broker_url = getattr(settings, "CELERY_BROKER_URL", "amqp://admin:admin@rabbitmq:5672//")
        exchange = Exchange("runs", type="topic")
        queue_name = f"appeals.ws.{self.event_id}"
        routing_key = f"runs.{self.event_id}"
        try:
            with Connection(broker_url) as conn:
                q = Queue(queue_name, exchange=exchange, routing_key=routing_key, durable=False, auto_delete=True)
                with conn.channel() as channel:
                    bq = q(channel)
                    bq.declare()
                    while not getattr(self, "_stop", False):  # type: ignore[attr-defined]
                        msg = bq.get(no_ack=True)
                        if not msg:
                            time.sleep(0.3)
                            continue
                        payload = msg.payload or {}
                        event_type = payload.get("event")
                        if event_type == "appeal_outcome":
                            data = payload.get("data", {})
                            # Forward to group; the async handler will send to socket
                            from asgiref.sync import async_to_sync
                            async_to_sync(self.channel_layer.group_send)(  # type: ignore[arg-type]
                                self.group_name,
                                {"type": "appeals.message", "data": data},
                            )
        except Exception:
            # Silently exit on connection errors
            return


class EchoConsumer(AsyncWebsocketConsumer):
    """A simple WebSocket consumer that echoes received messages."""

    async def connect(self) -> None:
        # Accept the incoming WebSocket connection.  In a real application
        # you should perform authentication here.
        await self.accept()
        await self.send_text("Echo server connected. Send a message to receive it back.")

    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None) -> None:
        if text_data is not None:
            # Echo the text back to the client.  You could also broadcast
            # the message to a group or perform other logic here.
            await self.send_text(f"Echo: {text_data}")
        elif bytes_data is not None:
            # If a binary message is received, we do nothing in this stub.
            pass

    async def disconnect(self, close_code: int) -> None:
        # Called when the socket closes.  Perform any cleanup here.
        pass