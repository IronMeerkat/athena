from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class PushMessage:
    target: str  # "browser" | "android" | "all"
    kind: str  # "info" | "block_signal" | "unblock_signal"
    title: str
    body: str
    meta: Optional[Dict[str, Any]] = None  # e.g., {"package": "...", "url": "...", "minutes": 15}


class PushGateway:
    """Abstract push gateway.

    This is a placeholder interface; provide concrete implementations later.
    """

    def send(self, message: PushMessage) -> bool:  # pragma: no cover - to be implemented later
        return False


class NoopPushGateway(PushGateway):
    def send(self, message: PushMessage) -> bool:  # pragma: no cover
        # Intentionally no-op for now; frontends will implement receivers later.
        return True



