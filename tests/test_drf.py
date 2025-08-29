import json
import time
from typing import Dict, Any

import pytest

from custom_session import custom_session
from custom_ws import custom_ws


@pytest.mark.integration
def test_ping_ok():
    resp = custom_session.get("/api/ping/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.integration
def test_runs_create_queues_request():
    body: Dict[str, Any] = {"agent_id": "echo", "input": {"text": "hi"}}
    resp = custom_session.post("/api/runs/", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data and isinstance(data["run_id"], str)
    assert data.get("queued") is True


@pytest.mark.integration
def test_device_attempt_and_sse_stream():
    attempt = {"device_id": "dev-xyz", "app": "pytest", "url": "https://example"}
    resp = custom_session.post("/api/device/attempt", json=attempt)
    assert resp.status_code == 200
    payload = resp.json()
    run_id = payload["run_id"]
    assert payload["decision"] == "pending"
    assert payload["sse"].startswith("/api/runs/")

    # Probe the SSE stream; expect initial comment and/or heartbeat
    sse_resp = custom_session.get(payload["sse"], stream=True)
    try:
        assert sse_resp.status_code == 200
        assert sse_resp.headers.get("Content-Type", "").startswith("text/event-stream")
        # Read a couple of lines to confirm stream is alive
        line_iter = sse_resp.iter_lines(chunk_size=1, decode_unicode=True)
        lines = []
        for _ in range(3):
            try:
                line = next(line_iter)
                lines.append(line)
                if len(lines) >= 2:
                    break
            except StopIteration:
                break
        assert any(l.startswith(":") for l in lines) or any(l.startswith("event:") for l in lines)
    finally:
        try:
            sse_resp.close()
        except Exception:
            pass


@pytest.mark.integration
def test_jwt_obtain_pair_invalid_creds():
    resp = custom_session.post("/api/token/", json={"username": "nouser", "password": "bad"})
    assert resp.status_code in (400, 401)


@pytest.mark.integration
def test_jwt_verify_invalid_token():
    resp = custom_session.post("/api/token/verify/", json={"token": "not-a-jwt"})
    assert resp.status_code in (401, 403, 400)


@pytest.mark.integration
def test_jwt_refresh_invalid_refresh():
    resp = custom_session.post("/api/token/refresh/", json={"refresh": "invalid"})
    assert resp.status_code in (401, 403, 400)


@pytest.mark.integration
def test_ws_echo_roundtrip():
    conn = custom_ws.connect("/ws/echo/")
    try:
        # initial server greeting
        greeting = conn.recv_json(timeout=2.0)
        assert "Echo" in greeting.get("data", "") or "connected" in greeting.get("data", "").lower()

        conn.send_json({"hello": "world"})
        # The consumer echoes text messages; our JSON becomes text once serialized
        echoed = conn.recv_json(timeout=2.0)
        assert "Echo:" in echoed.get("data", "")
    finally:
        conn.close()


@pytest.mark.integration
def test_ws_appeals_broadcast_event():
    event_id = "pytest-event-appeals"
    conn = custom_ws.connect(f"/ws/appeals/{event_id}")
    try:
        # Send arbitrary data (not type="appeal") to trigger group broadcast path
        payload = {"foo": "bar", "n": 1}
        conn.send_json(payload)

        def is_broadcast(msg: Dict[str, Any]) -> bool:
            return msg.get("type") == "event" and msg.get("data") == payload

        for msg in conn.iter_until(is_broadcast, max_seconds=3.0):
            if is_broadcast(msg):
                break
    finally:
        conn.close()

from custom_ws import custom_ws

