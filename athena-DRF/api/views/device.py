from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from celery import current_app as celery_app
from django.http import HttpRequest
from rest_framework.response import Response
from rest_framework.views import APIView

from athena_logging import get_logger

logger = get_logger(__name__)
class DeviceAttemptView(APIView):
    """POST /api/device/attempt

    Body: {"device_id": str, "event_id": str?, "app": str?,
    "url": str?, "ts": str?}
    Returns: {"run_id": str, "decision": "pending",
    "sse": "/api/runs/{id}/events"}
    """

    def post(self, request: HttpRequest) -> Response:  # type: ignore[override]
        logger.info(f"DeviceAttemptView: {request.data}")
        data = request.data
        # Accept missing event_id by generating one
        event_id = data.get("event_id") or str(uuid.uuid4())

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

        celery_app.send_task(
            "runs.execute_graph",
            args=[event_id, "guardian", {**data, "event_id": event_id}, manifest],
            queue=queue,
        )

        return Response(
            {
                "run_id": event_id,
                "decision": "pending",
                "sse": f"/api/runs/{event_id}/events",
            }
        )


class DevicePermitView(APIView):
    """POST /api/device/permit

    Body: {"event_id": str, "ttl_minutes": int}
    Returns: {"granted": bool, "until": iso8601}
    """

    def post(self, request: HttpRequest) -> Response:  # type: ignore[override]
        data = request.data
        ttl = max(0, int(data.get("ttl_minutes", 0)))
        until = datetime.now() + timedelta(minutes=ttl)
        logger.info(f"DevicePermitView: {data}")
        # In a real impl, sign a permit token and notify device controller
        return Response(
            {
                "granted": ttl > 0,
                "until": until.replace(tzinfo=None).isoformat() + "Z",
            }
        )


