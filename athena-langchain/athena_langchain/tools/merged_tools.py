from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Tuple, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, create_model
try:
    # pydantic v2
    from pydantic import ConfigDict  # type: ignore
except Exception:  # pragma: no cover - fallback for older environments
    ConfigDict = dict  # type: ignore

from athena_logging import get_logger
from athena_langchain.tools.registry import SENSITIVE_TOOLS, ToolSpec
from athena_langchain.tools.mongo_admin import _json_safe

logger = get_logger(__name__)


# -----------------
# Local registry → BaseTool wrappers
# -----------------

def _sanitize_name(name: str) -> str:
    import re
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)


class _AllowExtraModel(BaseModel):
    # Allow arbitrary extra keys so schema mismatches don't block tool use
    try:
        model_config = ConfigDict(extra="allow")  # type: ignore[attr-defined]
    except Exception:  # pydantic v1 fallback
        class Config:  # type: ignore[no-redef]
            extra = "allow"


def _json_type_to_py(t: str) -> type:
    if t == "string":
        return str
    if t == "integer":
        return int
    if t == "number":
        return float
    if t == "boolean":
        return bool
    if t == "object":
        return dict
    if t == "array":
        return list
    return Any


def _args_model_from_schema(tool_name: str, schema: Dict[str, Any] | None) -> Type[BaseModel]:
    if not schema or not isinstance(schema, dict):
        return create_model(f"{_sanitize_name(tool_name)}Args", __base__=_AllowExtraModel)  # type: ignore[arg-type]

    properties: Dict[str, Any] = schema.get("properties") or {}
    required: List[str] = list(schema.get("required") or [])
    fields: Dict[str, Tuple[type, Any]] = {}
    for key, prop in properties.items():
        if not isinstance(prop, dict):
            py_t = Any
        else:
            py_t = _json_type_to_py(str(prop.get("type")))
        default = ... if key in required else None
        fields[key] = (py_t, Field(default=default, description=str(prop.get("description", ""))))

    # Fallback to allow extras beyond the declared properties
    return create_model(
        f"{_sanitize_name(tool_name)}Args",
        __base__=_AllowExtraModel,
        **fields,  # type: ignore[arg-type]
    )


class RegistryTool(BaseTool):
    """LangChain BaseTool wrapper around a registry tool function."""

    registry_name: str
    description: str
    args_schema: Type[BaseModel]  # type: ignore[assignment]

    def _run(self, **kwargs: Any) -> str:
        try:
            result = SENSITIVE_TOOLS.call(self.registry_name, kwargs)
            return json.dumps(_json_safe(result))
        except Exception as e:  # noqa: BLE001
            logger.exception("Registry tool %s failed", self.registry_name)
            raise e

    async def _arun(self, **kwargs: Any) -> str:  # pragma: no cover
        # Synchronous tools are sufficient for our current use; add aio path later if needed.
        return self._run(**kwargs)


def local_registry_as_base_tools() -> List[BaseTool]:
    tools: List[BaseTool] = []
    for name, spec in SENSITIVE_TOOLS.list().items():
        args_model = _args_model_from_schema(name, spec.schema)
        tool = RegistryTool(
            name=_sanitize_name(name),
            registry_name=name,
            description=spec.description,
            args_schema=args_model,
        )
        tools.append(tool)
    return tools


# -----------------
# MCP (stdio) → BaseTools via adapters
# -----------------

_MCP_TOOLS: List[BaseTool] | None = None
_MCP_LOCK = asyncio.Lock()


async def _load_mcp_tools() -> List[BaseTool]:
    global _MCP_TOOLS
    async with _MCP_LOCK:
        if _MCP_TOOLS is not None:
            return _MCP_TOOLS
        servers_raw = os.getenv("ATHENA_MCP_SERVERS")
        if servers_raw:
            try:
                servers = json.loads(servers_raw)
            except Exception:
                logger.exception("Invalid ATHENA_MCP_SERVERS JSON; falling back to stdio default")
                servers = {}
        else:
            # Default: spawn this repo's stdio server as a child process
            servers = {
                "athena": {
                    "command": sys.executable,
                    "args": ["-m", "athena_langchain.mcp.server"],
                    "transport": "stdio",
                }
            }
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient

            client = MultiServerMCPClient(servers)
            tools = await client.get_tools()
            _MCP_TOOLS = tools
            return tools
        except Exception as e:  # noqa: BLE001
            logger.exception("Failed to load MCP tools: %s", e)
            _MCP_TOOLS = []
            return []


def get_merged_tools_sync() -> List[BaseTool]:
    """Return merged list of BaseTools: local registry + MCP stdio tools.

    This function blocks the calling thread to complete async MCP loading once per
    process and caches the result for subsequent calls.
    """
    local = local_registry_as_base_tools()
    try:
        mcp = asyncio.run(_load_mcp_tools())
    except RuntimeError:
        # If we're already in an event loop (rare in Celery), fall back to no MCP tools
        logger.warning("Running inside an event loop; skipping MCP tool load")
        mcp = []

    # Prefer local tools over MCP duplicates (same logical tool exposed via MCP stdio)
    local_names = {t.name for t in local}
    deduped_mcp: List[BaseTool] = []
    for t in mcp:
        try:
            # If the MCP tool's sanitized name matches a local tool name, skip it
            if _sanitize_name(getattr(t, "name", "")) in local_names:
                continue
        except Exception:
            pass
        deduped_mcp.append(t)

    merged: List[BaseTool] = [*local, *deduped_mcp]
    # Ensure unique names across all tools
    seen: Dict[str, int] = {}
    for t in merged:
        base = t.name
        if base not in seen:
            seen[base] = 1
            continue
        i = seen[base] + 1
        new_name = f"{base}_{i}"
        # Increment until unique
        while new_name in seen:
            i += 1
            new_name = f"{base}_{i}"
        try:
            t.name = new_name  # type: ignore[assignment]
        except Exception:
            # As a last resort, leave as-is and log
            logger.warning("Could not rename tool %s to avoid collision", base)
            continue
        seen[base] = i
        seen[new_name] = 1

    return merged


def to_openai_function_specs(tools: List[BaseTool]) -> List[dict]:
    specs: List[dict] = []
    for t in tools:
        try:
            schema = (
                t.args_schema.model_json_schema()  # type: ignore[attr-defined]
                if getattr(t, "args_schema", None) is not None
                else {"type": "object"}
            )
        except Exception:
            logger.exception("Failed to build JSON schema for tool %s", getattr(t, "name", "<unnamed>"))
            schema = {"type": "object"}
        specs.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": getattr(t, "description", "") or "",
                "parameters": schema,
            },
        })
    return specs


