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
from celery.result import AsyncResult
import logging
import sys

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("athena_mcp")


def _json(v: Any) -> str:
    try:
        return json.dumps(v)
    except (TypeError, ValueError):
        return json.dumps({"_repr": str(v)})


server = Server("athena-langchain")


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
            description="List registered tools (public and sensitive)",
            inputSchema={"type": "object"},
        ),
        Tool(
            name="tools.call",
            description=(
                "Call a registered tool by name. "
                "Input: {name, args?, scope?=sensitive|public}"
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
        run_id = str(params.get("run_id", ""))
        agent_id = str(params.get("agent_id", ""))
        payload = params.get("payload")
        manifest = params.get("manifest") or {}
        queue = str(manifest.get("queue", "public"))
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
        run_id = str(params.get("run_id", ""))
        agent_id = str(params.get("agent_id", ""))
        payload = params.get("payload")
        manifest = params.get("manifest") or {}
        queue = str(manifest.get("queue", "public"))
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
        task_id = str(params.get("task_id", ""))
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

    if name.startswith("policy."):
        # Route to tool registry to avoid duplicating Celery tasks
        reg = SENSITIVE_TOOLS
        try:
            res = reg.call(name, params)
        except (KeyError, ValueError, TypeError) as e:
            res = {"error": str(e)}
        return [
            TextContent(
                type="text",
                text=_json(res),
            )
        ]

    if name == "tools.list":
        pub = {k: v.description for k, v in PUBLIC_TOOLS.list().items()}
        sen = {k: v.description for k, v in SENSITIVE_TOOLS.list().items()}
        return [
            TextContent(
                type="text",
                text=_json({"public": pub, "sensitive": sen}),
            )
        ]
    if name == "tools.call":
        tool_name = str(params.get("name", ""))
        scope = str(params.get("scope", "sensitive"))
        args = params.get("args") or {}
        reg = PUBLIC_TOOLS if scope == "public" else SENSITIVE_TOOLS
        try:
            res = reg.call(tool_name, args)
        except (KeyError, ValueError, TypeError) as e:
            res = {"error": str(e)}
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
