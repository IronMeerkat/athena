from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from celery import current_app as celery_app
from django.http import HttpRequest
from rest_framework.response import Response
from rest_framework.views import APIView


class DeviceAttemptView(APIView):
    """POST /api/device/attempt

    Body: {"device_id": str, "event_id": str?, "app": str?,
    "url": str?, "ts": str?}
    Returns: {"run_id": str, "decision": "pending",
    "sse": "/api/runs/{id}/events"}
    """

    def post(self, request: HttpRequest) -> Response:  # type: ignore[override]
        print(f"DeviceAttemptView: {request.data}")
        data = request.data or {}
        event_id = data.get("event_id") or str(uuid.uuid4())
        attempt = {
            "device_id": data.get("device_id"),
            "app": data.get("app"),
            "url": data.get("url"),
            "ts": data.get("ts"),
            "event_id": event_id,
        }

        # Route owner attempts to sensitive by default; guests to public
        queue = "sensitive"
        manifest = {
            "agent_ids": ["guardian"],
            "tool_ids": [],
            "memory_namespaces": [],
            "queue": queue,
            "max_tokens": 2000,
            "max_cost_cents": 10,
            "metadata": {"event_id": event_id},
        }

        run_id = event_id
        celery_app.send_task(
            "runs.execute_graph",
            args=[run_id, "guardian", attempt, manifest],
            queue=queue,
        )

        return Response(
            {
                "run_id": run_id,
                "decision": "pending",
                "sse": f"/api/runs/{run_id}/events",
            }
        )


class DevicePermitView(APIView):
    """POST /api/device/permit

    Body: {"event_id": str, "ttl_minutes": int}
    Returns: {"granted": bool, "until": iso8601}
    """

    def post(self, request: HttpRequest) -> Response:  # type: ignore[override]
        data = request.data or {}
        ttl = max(0, int(data.get("ttl_minutes", 0)))
        until = datetime.utcnow() + timedelta(minutes=ttl)
        print(f"DevicePermitView: {data}")
        # In a real impl, sign a permit token and notify device controller
        return Response(
            {
                "granted": ttl > 0,
                "until": until.replace(tzinfo=None).isoformat() + "Z",
            }
        )


