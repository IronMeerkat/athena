from __future__ import annotations

import asyncio
import json
from typing import Any, Dict
from mcp.server import Server
from mcp.types import (
    CallToolRequest,
    ListToolsRequest,
    TextContent,
    Tool
)

from athena_langchain.tasks.run_graph import run_graph
from athena_langchain.tasks.agents import (
    list_public_agents,
    list_sensitive_agents,
)
from athena_langchain.tools.registry import SENSITIVE_TOOLS, PUBLIC_TOOLS
# Ensure policy tools register on import
from athena_langchain.tools.policies import (  # noqa: F401
    __init__ as _policy_tools,
)
# Ensure mongo tool registers on import
from athena_langchain.tools import mongo_admin  # noqa: F401
from celery.result import AsyncResult
from athena_logging import get_logger
import sys

logger = get_logger(__name__)

def _json(v: Any) -> str:
    try:
        return json.dumps(v)
    except (TypeError, ValueError):
        return json.dumps({"_repr": str(v)})


server = Server("athena-langchain")


# Per-run capability context for allowlisting tools/agents.
# Seeded when a run is initiated and consulted by tools.list/tools.call/policy.*
RUN_CONTEXTS: dict[str, dict[str, Any]] = {}


def _seed_run_context(run_id: str, manifest: Dict[str, Any]) -> None:

    agent_ids = manifest["agent_ids"]
    tool_ids = manifest["tool_ids"]
    queue = manifest.get("queue", "public")

    RUN_CONTEXTS[run_id] = {
        "agent_ids": agent_ids,
        "tool_ids": tool_ids,
        "queue": queue,
    }
    logger.info(
        "Seeded run context: run_id=%s agents=%s tools=%s queue=%s",
        run_id,
        agent_ids,
        tool_ids,
        queue,
    )


def _get_run_context(run_id: str) -> Dict[str, Any] | None:
    return RUN_CONTEXTS.get(run_id)


def _validate_required(schema: Dict[str, Any] | None, args: Dict[str, Any]) -> None:
    """Minimal JSON-schema 'required' validator."""
    if not schema:
        return

    missing = [k for k in schema['required'] if k not in args]
    if missing:
        logger.error("Missing required argument(s): %s", ", ".join(missing))
        raise ValueError(f"Missing required argument(s): {', '.join(missing)}")


@server.list_tools()
async def handle_list_tools(_req: ListToolsRequest) -> list[Tool]:
    # Agent surface
    logger.info("list_tools requested")
    tools: list[Tool] = [
        Tool(
            name="agents.list_public",
            description="List public agents registered in Athena",
            inputSchema={"type": "object"},
        ),
        Tool(
            name="agents.list_sensitive",
            description="List sensitive agents registered in Athena",
            inputSchema={"type": "object"},
        ),
        Tool(
            name="runs.execute",
            description=(
                "Execute an agent run via Celery. "
                "Input: {run_id, agent_id, payload, manifest}"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "payload": {},
                    "manifest": {},
                },
                "required": ["run_id", "agent_id", "payload"],
            },
        ),
        Tool(
            name="runs.execute_async",
            description=(
                "Queue an agent run and return task_id. "
                "Input: {run_id, agent_id, payload, manifest}"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "payload": {},
                    "manifest": {},
                },
                "required": ["run_id", "agent_id", "payload"],
            },
        ),
        Tool(
            name="runs.status",
            description=(
                "Get Celery task status. "
                "Input: {task_id}; returns {state, ready, result?}"
            ),
            inputSchema={
                "type": "object",
                "properties": {"task_id": {"type": "string"}},
                "required": ["task_id"],
            },
        ),
        # Policy (routed to tool registry)
        Tool(
            name="policy.schedule_get",
            description="Get schedule for a user_key (session id)",
            inputSchema={
                "type": "object",
                "properties": {"user_key": {"type": "string"}},
                "required": ["user_key"],
            },
        ),
        Tool(
            name="policy.schedule_set",
            description="Set schedule for a user_key (session id)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_key": {"type": "string"},
                    "schedule": {"type": "array"},
                },
                "required": ["user_key", "schedule"],
            },
        ),
        Tool(
            name="policy.strictness_get",
            description="Compute strictness for now for a user_key",
            inputSchema={
                "type": "object",
                "properties": {"user_key": {"type": "string"}},
                "required": ["user_key"],
            },
        ),
        Tool(
            name="policy.goal_get",
            description="Get current timeblock goal for a user_key",
            inputSchema={
                "type": "object",
                "properties": {"user_key": {"type": "string"}},
                "required": ["user_key"],
            },
        ),
        # Tool registry passthrough
        Tool(
            name="tools.list",
            description=(
                "List registered tools (public and sensitive). "
                "Optional: {run_id} to filter to the current run's allowlist."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string"},
                },
            },
        ),
        Tool(
            name="tools.call",
            description=(
                "Call a registered tool by name. "
                "Input: {name, args?, scope?=sensitive|public, run_id?}"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "args": {"type": "object"},
                    "scope": {
                        "type": "string",
                        "enum": ["public", "sensitive"],
                    },
                    "run_id": {"type": "string"},
                },
                "required": ["name"],
            },
        ),
    ]
    return tools


@server.call_tool()
async def handle_call_tool(req: CallToolRequest) -> list[TextContent]:
    name = req.name
    params = req.arguments or {}
    logger.info("call_tool: name=%s params=%s", name, params)

    if name == "agents.list_public":
        # Route to public queue so a listening worker will pick it up
        result = await asyncio.to_thread(
            lambda: list_public_agents.apply_async(queue="public").get()
        )
        return [
            TextContent(
                type="text",
                text=_json(result),
            )
        ]
    if name == "agents.list_sensitive":
        result = await asyncio.to_thread(
            lambda: list_sensitive_agents.apply_async(queue="sensitive").get()
        )
        return [
            TextContent(
                type="text",
                text=_json(result),
            )
        ]
    if name == "runs.execute":
        # Strict parameter access; raise on missing/wrong types
        run_id = params["run_id"]
        agent_id = params["agent_id"]
        payload = params["payload"]
        manifest = params.get("manifest") or {"queue": "sensitive"}
        queue = manifest.get("queue", "sensitive")
        # Ignore allowlists/manifests by request; still seed minimal context
        _seed_run_context(run_id, manifest)
        # Execute synchronously and return result
        out = await asyncio.to_thread(
            lambda: run_graph.apply_async(
                kwargs={
                    "run_id": run_id,
                    "agent_id": agent_id,
                    "payload": payload,
                    "manifest": manifest,
                },
                queue=queue,
            ).get()
        )
        return [
            TextContent(
                type="text",
                text=_json(out),
            )
        ]

    if name == "runs.execute_async":
        run_id = params["run_id"]
        agent_id = params["agent_id"]
        payload = params["payload"]
        manifest = params.get("manifest") or {"queue": "sensitive"}
        queue = manifest.get("queue", "sensitive")
        _seed_run_context(run_id, manifest)
        async_res = await asyncio.to_thread(
            lambda: run_graph.apply_async(
                kwargs={
                    "run_id": run_id,
                    "agent_id": agent_id,
                    "payload": payload,
                    "manifest": manifest,
                },
                queue=queue,
            )
        )
        return [
            TextContent(
                type="text",
                text=_json({"task_id": async_res.id}),
            )
        ]

    if name == "runs.status":
        task_id = params["task_id"]
        ar = AsyncResult(task_id)
        payload: Dict[str, Any] = {"state": ar.state, "ready": ar.ready()}
        if ar.successful():
            payload["result"] = ar.result
        elif ar.failed():
            payload["error"] = str(ar.result)
        return [
            TextContent(
                type="text",
                text=_json(payload),
            )
        ]

    if name.startswith("policy.") or name.startswith("agents.") or name.startswith("mongo."):
        # Route to tool registry; ignore allowlists for now
        reg = SENSITIVE_TOOLS
        specs = reg.list()
        spec = specs.get(name)
        if not spec:
            logger.error("Unknown tool: %s", name)
            raise KeyError(f"Unknown tool: {name}")
        # Minimal required-keys validation
        _validate_required(spec.schema, params)
        res = reg.call(name, params)
        return [TextContent(type="text", text=_json(res))]

    if name == "tools.list":
        # Optional run_id filtering
        run_id_filter = params.get("run_id")
        pub = {k: v.description for k, v in PUBLIC_TOOLS.list().items()}
        sen = {k: v.description for k, v in SENSITIVE_TOOLS.list().items()}
        return [
            TextContent(
                type="text",
                text=_json({"public": pub, "sensitive": sen}),
            )
        ]
    if name == "tools.call":
        tool_name = params["name"]
        scope = params.get("scope", "sensitive")
        args = params.get("args", {})
        reg = PUBLIC_TOOLS if scope == "public" else SENSITIVE_TOOLS
        specs = reg.list()
        spec = specs.get(tool_name)
        if not spec:
            logger.error("Unknown tool: %s", tool_name)
            raise KeyError(f"Unknown tool: {tool_name}")
        _validate_required(spec.schema, args)
        res = reg.call(tool_name, args)
        return [TextContent(type="text", text=_json(res))]

    return [
        TextContent(
            type="text",
            text=_json({"error": f"Unknown tool {name}"}),
        )
    ]


def main() -> None:
    async def _run() -> None:
        # Use official stdio transport helper from MCP
        try:
            from mcp.server.stdio import stdio_server  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "MCP stdio transport not available "
                "(mcp.server.stdio.stdio_server)"
            ) from e

        logger.info("Initializing MCP stdio server (athena-langchain)")
        async with stdio_server() as (read, write):
            logger.info("MCP stdio transport established; starting server.run")
            init_opts = server.create_initialization_options()
            await server.run(
                read, write, init_opts
            )  # type: ignore[attr-defined]

    asyncio.run(_run())


if __name__ == "__main__":
    main()
