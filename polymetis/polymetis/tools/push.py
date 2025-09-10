from __future__ import annotations

from typing import Any, Dict

from polymetis.tools.registry import SENSITIVE_TOOLS as TOOL_REGISTRY, ToolSpec


def _send_push(args: Dict[str, Any]) -> Dict[str, Any]:
    # Return a handoff payload that the gateway will dispatch via Celery.
    return {
        "handoff": "gateway.dispatch_push",
        "payload": {
            "target": str(args.get("target", "all")),
            "kind": str(args.get("kind", "info")),
            "title": str(args.get("title", "")),
            "body": str(args.get("body", "")),
            "meta": args.get("meta"),
        },
    }


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


