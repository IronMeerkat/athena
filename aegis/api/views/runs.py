from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict

from celery import current_app as celery_app
from django.conf import settings
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from kombu import Connection, Exchange, Queue
from kombu.exceptions import KombuError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class RunsCreateView(APIView):
    """POST /api/runs

    Body: {"agent_id": str, "input": Any, "options": {"stream": bool}}
    Returns: {"run_id": str, "queued": true}
    """

    def post(self, request: HttpRequest) -> Response:  # type: ignore[override]
        data = request.data or {}
        agent_id = str(data.get("agent_id", "")).strip()
        payload = data.get("input")
        options = data.get("options") or {}
        if not agent_id:
            return Response(
                {"error": "agent_id required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build a minimal capability manifest based on user/role. For now,
        # route owner to sensitive if flagged in request.
        queue = "sensitive" if options.get("sensitive") else "public"
        manifest: Dict[str, Any] = {
            "agent_ids": [agent_id],
            "tool_ids": [],
            "memory_namespaces": [],
            "queue": queue,
            "max_tokens": 20000,
            "max_cost_cents": 50,
            "metadata": {
                "actor": str(getattr(request.user, "username", "anon"))
            },
        }

        run_id = str(uuid.uuid4())

        # Enqueue to correct queue
        # Use send_task to avoid importing worker code into gateway
        celery_app.send_task(
            "runs.execute_graph",
            args=[run_id, agent_id, payload, manifest],
            queue=queue,
        )

        return Response({"run_id": run_id, "queued": True})


class RunEventsSSEView(View):
    """GET /api/runs/{run_id}/events -> text/event-stream

    Listens to RabbitMQ topic "runs.{run_id}" and forwards messages as SSE.
    """

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):  # type: ignore[override]
        return super().dispatch(*args, **kwargs)

    def get(
        self,
        request: HttpRequest,
        run_id: str,
    ) -> HttpResponse:  # type: ignore[override]
        _ = request
        broker_url = getattr(settings, "CELERY_BROKER_URL",
                             "amqp://admin:admin@rabbitmq:5672//")
        exchange = Exchange("runs", type="topic")
        queue_name = f"sse.{run_id}"
        routing_key = f"runs.{run_id}"

        def event_stream():
            # Yield an initial comment to start SSE
            yield b": ok\n\n"
            try:
                with Connection(broker_url) as conn:
                    q = Queue(
                        queue_name,
                        exchange=exchange,
                        routing_key=routing_key,
                        durable=False,
                        auto_delete=True,
                    )
                    with conn.channel() as channel:
                        bq = q(channel)
                        bq.declare()
                        for _ in range(1_000_000):  # TODO ???
                            message = bq.get(no_ack=True)
                            if not message:
                                # Heartbeat every second
                                yield b": heartbeat\n\n"
                                time.sleep(1)
                                continue
                            payload = message.payload or {}
                            event = payload.get("event", "message")
                            data = json.dumps(
                                payload.get("data", {})
                            ).encode("utf-8")
                            yield b"event: " + event.encode("utf-8") + b"\n"
                            yield b"data: " + data + b"\n\n"
            except KombuError:
                # On error, close the stream
                yield b"event: error\ndata: {}\n\n"

        resp = StreamingHttpResponse(event_stream(),
                                     content_type="text/event-stream")
        resp["Cache-Control"] = "no-cache"
        return resp
