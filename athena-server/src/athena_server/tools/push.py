from __future__ import annotations

from typing import Any, Dict

from athena_server.tools.registry import REGISTRY as TOOL_REGISTRY, ToolSpec
from athena_server.notifications import NoopPushGateway, PushMessage


_gateway = NoopPushGateway()


def _send_push(args: Dict[str, Any]) -> Dict[str, Any]:
    target = str(args.get("target", "all"))
    kind = str(args.get("kind", "info"))
    title = str(args.get("title", ""))
    body = str(args.get("body", ""))
    meta = args.get("meta")
    ok = _gateway.send(PushMessage(target=target, kind=kind, title=title, body=body, meta=meta))
    return {"ok": bool(ok)}


TOOL_REGISTRY.register(
    ToolSpec(
        name="push_send",
        description=(
            "Send a push message to browser and/or android frontends. "
            "This is a placeholder gateway; frontends will implement receivers later."
        ),
        schema={
            "type": "object",
            "properties": {
                "target": {"type": "string", "enum": ["browser", "android", "all"]},
                "kind": {"type": "string", "enum": ["info", "block_signal", "unblock_signal"]},
                "title": {"type": "string"},
                "body": {"type": "string"},
                "meta": {"type": "object"},
            },
            "required": ["target", "kind", "title", "body"],
        },
    ),
    _send_push,
)


