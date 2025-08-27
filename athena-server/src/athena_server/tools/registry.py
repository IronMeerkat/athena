from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


@dataclass
class ToolSpec:
    name: str
    description: str
    schema: Optional[dict] = None


ToolFunc = Callable[[dict], Any]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, tuple[ToolSpec, ToolFunc]] = {}

    def register(self, spec: ToolSpec, func: ToolFunc) -> None:
        if spec.name in self._tools:
            raise ValueError(f"Tool already registered: {spec.name}")
        self._tools[spec.name] = (spec, func)

    def call(self, name: str, args: Optional[dict] = None) -> Any:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        _, func = self._tools[name]
        return func(args or {})

    def list(self) -> Dict[str, ToolSpec]:
        return {k: v[0] for k, v in self._tools.items()}


REGISTRY = ToolRegistry()


# Example tools

def _echo(args: dict) -> dict:
    return {"echo": args}


def _sum(args: dict) -> dict:
    values = args.get("values", [])
    total = sum(v for v in values if isinstance(v, (int, float)))
    return {"total": total}


REGISTRY.register(ToolSpec(name="echo", description="Echo input arguments"), _echo)
REGISTRY.register(
    ToolSpec(
        name="sum", description="Sum numeric array values", schema={"type": "object", "properties": {"values": {"type": "array"}}}
    ),
    _sum,
)
