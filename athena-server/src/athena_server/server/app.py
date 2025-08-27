from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from langserve import add_routes
from importlib import import_module

# Ensure agents register on import (load modules for side effects)
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from athena_server.config import Settings
from athena_server.agents.registry import REGISTRY
from athena_server.tools.registry import REGISTRY as TOOL_REGISTRY

for _mod in (
    "athena_server.agents.example_rag_agent",
    "athena_server.agents.anti_distraction_agent",
    "athena_server.agents.goals_scheduler_agent",
    "athena_server.agents.appeals_agent",
):
    try:
        import_module(_mod)
    except ImportError:  # noqa: F401
        # If an agent fails to load, continue starting the server.
        # Individual agent routes won't be added below if not registered.
        pass


settings = Settings()

app = FastAPI(title="Athena Server", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/agents")
def list_agents() -> Dict[str, Dict[str, Any]]:
    return {k: vars(v) for k, v in REGISTRY.list().items()}


# Dynamically add LangServe routes for each agent
for agent_id in list(REGISTRY.list().keys()):
    entry = REGISTRY.get(agent_id)
    llm = REGISTRY.build_llm(settings, agent_id)
    graph = entry.build_graph(settings, llm)
    runnable = graph.compile()
    add_routes(app, runnable, path=f"/agents/{agent_id}")


@app.get("/tools")
def list_tools() -> Dict[str, Dict[str, Any]]:
    return {k: vars(v) for k, v in TOOL_REGISTRY.list().items()}


@app.post("/tools/{tool_name}")
def call_tool(tool_name: str, args: Dict[str, Any] | None = None) -> Any:
    try:
        return TOOL_REGISTRY.call(tool_name, args or {})
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e
