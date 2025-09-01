import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Generator, Optional

import websocket  # type: ignore


@dataclass
class WSMessage:
    type: str
    data: Any

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        try:
            return json.dumps({"type": self.type, "data": self.data})
        except Exception:
            return f"WSMessage(type={self.type}, data={self.data})"


class CustomWebSocket:
    def __init__(self, baseurl: str) -> None:
        # baseurl like ws://localhost:8000
        self.baseurl = baseurl.rstrip("/")

    def connect(self, path: str, timeout: float = 5.0) -> "ConnectedWebSocket":
        url = f"{self.baseurl}{path}"
        # Prefer websocket-client's helper; fallback to constructing WebSocket directly
        if hasattr(websocket, "create_connection"):
            ws = websocket.create_connection(url, timeout=timeout)  # type: ignore[attr-defined]
        elif hasattr(websocket, "WebSocket"):
            ws = websocket.WebSocket()
            if hasattr(ws, "settimeout"):
                try:
                    ws.settimeout(timeout)  # type: ignore[attr-defined]
                except Exception:
                    pass
            ws.connect(url)
        else:
            raise RuntimeError(
                "websocket-client is required: pip install websocket-client"
            )
        return ConnectedWebSocket(ws)


class ConnectedWebSocket:
    def __init__(self, ws: "websocket.WebSocket") -> None:
        self.ws = ws

    def send_json(self, payload: Dict[str, Any]) -> None:
        self.ws.send(json.dumps(payload))

    def recv_json(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        old = self.ws.gettimeout()
        if timeout is not None:
            self.ws.settimeout(timeout)
        try:
            raw = self.ws.recv()
        finally:
            if timeout is not None:
                self.ws.settimeout(old)
        try:
            return json.loads(raw)
        except Exception:
            return {"type": "text", "data": raw}

    def iter_until(self, predicate, max_seconds: float = 5.0) -> Generator[Dict[str, Any], None, None]:
        deadline = time.time() + max_seconds
        while time.time() < deadline:
            msg = self.recv_json(timeout=max(0.01, deadline - time.time()))
            print(f"Received message: {msg}")
            yield msg
            if predicate(msg):
                return
        raise TimeoutError("Condition not met before timeout")

    def close(self) -> None:
        try:
            self.ws.close()
        except Exception:
            pass


custom_ws = CustomWebSocket(baseurl="ws://localhost:8000")


