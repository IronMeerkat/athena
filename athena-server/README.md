## Athena Server
A boilerplate for an AI agent back-end built with LangChain, LangGraph, and LangServe. It exposes modular agents, a simple MCP-like tool registry, vector memory on Postgres (PGVector), and chat history on Redis.

### Features
- **Agents (LangGraph)**: Registry-based with per-agent model override
- **Tools (MCP-like)**: JSON-callable functions with a central registry
- **Vector memory (PGVector)**: Euclidean distance; ingestion CLI for your documents
- **Chat history (Redis)**: Session-based histories compatible with LangChain
- **LangServe (FastAPI)**: Auto-generated endpoints per agent with invoke/stream

---

## Prerequisites
- **Python**: 3.10+
- **Docker** and **Docker Compose**
- For OpenAI usage: set `OPENAI_API_KEY`
- For local models via Ollama: install `ollama` and set `OLLAMA_BASE_URL`

---

## Quickstart

### 1) Configure environment
Copy the example env and adjust values:
```bash
cp ops/env/.env.example .env
```
Important values:
- **Postgres**: `POSTGRES_*` (defaults are fine with compose)
- **Redis**: `REDIS_URL`
- **LLM**: `LLM_PROVIDER` (openai|ollama), `LLM_MODEL`
- **Embeddings**: `EMBEDDINGS_PROVIDER` (openai|ollama)

### 2) Start infrastructure
```bash
docker compose up -d
```
This starts Postgres (with PGVector) and Redis. PGVector extension is created automatically.

### 3) Install dependencies
```bash
pip install -e . -r requirements.txt
```

### 4) Ingest documents into vector memory
Use the ingestion CLI to embed your documents into PGVector:
```bash
python -m athena_server.memory.ingest_cli files ./docs
```
Options:
- `--glob` (default `**/*`) to match files in directories
- `--chunk-size` (default 1200), `--chunk-overlap` (default 150)
- `--collection` to use a non-default collection name
- `--dry-run` to preview parsing and splitting only

### 5) Run the API
```bash
python -m athena_server
```
The server will start on `APP_HOST:APP_PORT` from `.env` (default `0.0.0.0:8000`).

---

## Endpoints
Base URL examples assume `http://localhost:8000`.

### Health
- GET `/health`

### Agents
- GET `/agents` → list registered agents
- POST `/agents/{agent_id}/invoke` → run an agent once (LangServe)
- POST `/agents/{agent_id}/stream` → stream an agent run (SSE) (LangServe)

Example (invoke the example RAG agent):
```bash
curl -s http://localhost:8000/agents/example_rag/invoke \
  -H 'Content-Type: application/json' \
  -d '{"input": {"question": "What does Athena do?"}}' | jq .
```

### Tools
- GET `/tools` → list registered tools
- POST `/tools/{name}` → call a tool

Example:
```bash
curl -s http://localhost:8000/tools/sum \
  -H 'Content-Type: application/json' \
  -d '{"values": [1,2,3,4]}' | jq .
```

---

## Directory layout
```text
src/athena_server/
  __main__.py             # CLI entrypoint to run server (uvicorn)
  config.py               # Settings + LLM/Embedding factories
  server/app.py           # FastAPI app + LangServe route wiring

  db/
    postgres.py           # SQLAlchemy engine + extension ensure
    redis.py              # Redis client helper

  memory/
    chat_history.py       # Redis-backed chat history factory
    vectorstore.py        # PGVector vectorstore + retriever helpers
    ingest_cli.py         # Typer CLI for ingestion

  agents/
    __init__.py
    registry.py           # Agent registry + per-agent model override
    example_rag_agent.py  # Example LangGraph RAG agent

  tools/
    __init__.py
    registry.py           # MCP-like tool registry + example tools
```

---

## Configuration
Defined in `config.py` and loaded from `.env`.
- **LLM/Embeddings providers**: `openai` or `ollama`
- **Per-agent model override**: Declared in `agents/registry.py` via `AgentConfig.model_name`
- **Vector collection**: Default `VECTOR_COLLECTION` (per `.env`), can be overridden at ingestion time
- **Distance**: PGVector uses **Euclidean** distance by default in this boilerplate

---

## How to add a tool
Tools are registered in a central registry (`tools/registry.py`). You can:

### Option A: Register directly in `tools/registry.py`
1) Define a function that accepts a dict and returns any serializable result.
2) Define a `ToolSpec` and `REGISTRY.register` it.

Minimal example (pseudo):
```python
from athena_server.tools.registry import REGISTRY, ToolSpec

def _weather(args: dict) -> dict:
    city = args.get("city", "")
    # ... call a weather API ...
    return {"city": city, "temp_c": 22.5}

REGISTRY.register(
    ToolSpec(
        name="weather",
        description="Get current weather by city",
        schema={"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
    ),
    _weather,
)
```
Now call it:
```bash
curl -s http://localhost:8000/tools/weather -H 'Content-Type: application/json' -d '{"city":"Berlin"}'
```

### Option B: Add a new module and import it on startup
- Create `src/athena_server/tools/my_tool.py` that registers itself with `REGISTRY` on import
- Import it in `server/app.py` (top-level) to ensure it registers at startup

---

## How to add an agent
Agents are LangGraph graphs registered in `agents/registry.py`. Each agent provides:
- A `build_graph(settings, llm) -> StateGraph` function
- A `AgentConfig` with `name`, `description`, and optional per-agent `model_name`
- Registration via `REGISTRY.register("agent_id", AgentEntry(...))`

Minimal skeleton:
```python
# src/athena_server/agents/my_agent.py
from langgraph.graph import StateGraph, END
from typing import TypedDict
from athena_server.agents.registry import REGISTRY, AgentConfig, AgentEntry
from athena_server.config import Settings

class MyState(TypedDict):
    input: str
    output: str

def build_graph(settings: Settings, llm):
    def step(state: MyState) -> MyState:
        state["output"] = f"Echo: {state['input']}"
        return state
    g = StateGraph(MyState)
    g.add_node("step", step)
    g.set_entry_point("step")
    g.add_edge("step", END)
    return g

REGISTRY.register(
    "my_agent",
    AgentEntry(
        config=AgentConfig(name="My Agent", description="Echoes input", model_name="gpt-4o-mini"),
        build_graph=build_graph,
    ),
)
```
Ensure it registers on startup by importing it in `server/app.py`:
```python
from athena_server.agents import example_rag_agent  # existing
from athena_server.agents import my_agent          # add this line
```
The agent will appear at:
- GET `/agents` and
- POST `/agents/my_agent/invoke` | `/agents/my_agent/stream`

### Using vector memory in an agent
- Get embeddings and vectorstore: `make_embeddings(settings)`, `get_vectorstore(settings, embeddings)`
- Create a retriever: `get_retriever(vectorstore, k=4)`
- Use within your nodes to ground generation

### Using chat history
- Use `memory/chat_history.py` to obtain a `RedisChatMessageHistory` factory, and integrate it into your chains/graphs as needed.

---

## Tips & patterns
- **Collections per domain/tenant**: pass `--collection` during ingestion and use the same in your agent to isolate memory
- **Per-agent models**: set `model_name` in `AgentConfig` to override the default model for that agent
- **CORS**: currently allows all origins; tighten in production
- **Secrets**: prefer environment variables and a secure secret manager in production

---

## Development
- Run infra: `docker compose up -d`
- Run API: `python -m athena_server`
- Ingest: `python -m athena_server.memory.ingest_cli files ./docs`
- Format/lint: follow existing style; avoid long lines where possible

---

## Advanced: Tools
This project’s tools are MCP-like: name, description, JSON schema, and an implementation. Best practices:
- **Pure functions**: deterministic for given inputs; no global state
- **Validation**: validate inputs (Pydantic or jsonschema) and return clear errors
- **Timeouts/retries**: for network calls (use `httpx` with timeouts)
- **Idempotency**: safe to retry
- **Observability**: log inputs/outputs (minus secrets) and durations
- **Namespaces**: group tools by domain (e.g., `tools/web/`, `tools/files/`)

### Tool with validation example
```python
# src/athena_server/tools/weather.py
from __future__ import annotations
from pydantic import BaseModel, Field
import httpx
from athena_server.tools.registry import REGISTRY, ToolSpec

class WeatherArgs(BaseModel):
    city: str = Field(..., min_length=1)

async def _weather_impl(args: dict) -> dict:
    data = WeatherArgs(**args)
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get("https://api.example.com/weather", params={"q": data.city})
        r.raise_for_status()
        body = r.json()
    return {"city": data.city, "temp_c": body.get("temp_c")}

# Register with schema for discoverability
REGISTRY.register(
    ToolSpec(
        name="weather.get",
        description="Get current weather by city",
        schema=WeatherArgs.model_json_schema(),
    ),
    # The registry accepts sync; adapt async with a small runner if needed
    lambda a: asyncio.run(_weather_impl(a)),
)
```
Ensure it imports at startup by adding in `server/app.py`:
```python
from athena_server.tools import weather  # noqa: F401
```

### Using tools from agents (LLM tool-calls)
To enable model tool-calling, convert registry tools to LangChain tools and bind to the LLM:
```python
# helper, e.g., src/athena_server/tools/lc_adapter.py
from langchain_core.tools import StructuredTool
from pydantic import create_model
from athena_server.tools.registry import REGISTRY

def make_langchain_tools_from_registry(names: list[str] | None = None):
    tools = []
    for name, spec in REGISTRY.list().items():
        if names and name not in names:
            continue
        schema = spec.schema or {"type": "object"}
        # Minimal Pydantic model from jsonschema properties
        fields = {k: (object, ...) for k in (schema.get("properties") or {}).keys()}
        Model = create_model(f"Args_{name.replace('.', '_')}", **fields)  # type: ignore[arg-type]
        tools.append(
            StructuredTool.from_function(
                func=lambda **kwargs: REGISTRY.call(name, kwargs),
                name=name,
                description=spec.description,
                args_schema=Model,
            )
        )
    return tools
```
Then inside an agent graph node:
```python
lc_tools = make_langchain_tools_from_registry(["weather.get"])  # select tools
bound_llm = llm.bind_tools(lc_tools)  # enables tool-calls for providers that support it
```

---

## Advanced: Agents
Design tips for scalable agents with LangGraph:
- **State design first**: define a minimal `TypedDict` for inputs/outputs across nodes
- **Small nodes**: one responsibility per node; compose with edges
- **Conditional routing**: route based on state to avoid unnecessary work
- **Tools as nodes**: wrap tool calls in nodes for clarity and retries
- **Checkpoints**: persist progress and resume; consider a checkpointer for long tasks
- **Subgraphs**: for reusable flows (e.g., a RAG subgraph)
- **Human-in-the-loop**: insert interrupt nodes for approvals

### Example: adding tool-enabled generation
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict
from athena_server.tools.lc_adapter import make_langchain_tools_from_registry

class ToolState(TypedDict):
    query: str
    answer: str

def build_graph(settings, llm):
    tools = make_langchain_tools_from_registry(["weather.get"])  # pick tools
    model = llm.bind_tools(tools)

    def generate(state: ToolState) -> ToolState:
        msg = model.invoke({"role": "user", "content": state["query"]})
        state["answer"] = getattr(msg, "content", str(msg))
        return state

    g = StateGraph(ToolState)
    g.add_node("generate", generate)
    g.set_entry_point("generate")
    g.add_edge("generate", END)
    return g
```

### Per-agent models
- Use `AgentConfig.model_name` to override the default `Settings.llm_model`
- If you also need custom embeddings per agent, derive a new `Settings` copy and use a dedicated embeddings model in your agent builder

---

## Advanced: Memory
There are two memory layers: conversation (Redis) and vector memory (PGVector).

### Conversation memory (Redis)
- Use `memory/chat_history.py` → `get_session_history_factory(settings)`
- Keep a session ID per user/thread; set TTL in Redis if desired
- Summarize long histories into a rolling summary with your LLM to control context size

Summary example:
```python
from langchain_core.prompts import ChatPromptTemplate

summarize = ChatPromptTemplate.from_messages([
    ("system", "Summarize the dialog into a compact memory for future turns."),
    ("human", "{dialog}"),
]) | llm
summary = summarize.invoke({"dialog": "..."}).content
```

### Vector memory (PGVector)
- Default distance is **Euclidean** in `memory/vectorstore.py`
- Use metadata to scope: `{ tenant, source, type, tags }`
- Filter at retrieval: `retriever = vs.as_retriever(search_kwargs={"k": 6, "filter": {"tenant": "acme"}})`
- Upserts/deletes: maintain your own `doc_id` in metadata and use `delete` as needed

Programmatic add/delete:
```python
vs = get_vectorstore(settings, make_embeddings(settings))
ids = vs.add_documents([
    {"page_content": "content", "metadata": {"doc_id": "x1", "tenant": "acme"}},
])
vs.delete({"filter": {"metadata": {"doc_id": "x1"}}})
```

### Retrieval quality
- Chunking: tune `chunk_size`/`overlap` per corpus
- Query transforms: HyDE or query rewriting before retrieval
- Reranking: add a cross-encoder rerank step to reorder retrieved docs
- Prompting: instruct the model to abstain when context is weak

---

## Advanced: Ingestion
Enhance `ingest_cli` to support loaders and metadata:
- Add loaders (PDF/HTML/MD): LangChain document loaders (`pip install pypdf beautifulsoup4 unstructured`)
- Extract metadata (title, headings, file path) and attach to `metadata`
- Deduplicate by hash of content chunk
- Reingest strategy: delete by `source` then re-add

Example extension (pseudo):
```python
from langchain_community.document_loaders import PyPDFLoader
loader = PyPDFLoader("/path/file.pdf")
docs = loader.load()
# Convert `docs` (Document objects) to {page_content, metadata} dicts for vs.add_documents
```

---

## Directory conventions for scale
Consider organizing by domain and function:
- `agents/` → subfolders per domain (`research/`, `support/`, `code/`), each with graphs and tests
- `tools/` → `providers/` (external APIs), `system/` (fs, web, search), `adapters/` (LangChain tool adapters)
- `prompts/` → reusable prompt templates and message catalogs
- `workflows/` → orchestrations combining multiple agents/tools
- `memory/strategies/` → retrieval/reranking strategies
- `scripts/` → ops scripts (migrations, maintenance)
- `evals/` → evaluation datasets and harnesses

Keep registration centralized (single import site per area) to control startup order.

---

## Operational notes
- **Auth**: add API keys/JWT to FastAPI routes; restrict tool endpoints in production
- **Rate limits**: per-tenant rate limiting (e.g., via Redis counters)
- **Observability**: log structured events; optionally integrate LangSmith or OpenTelemetry
- **Migrations**: manage Postgres schema via Alembic for non-PGVector tables
- **Multi-tenancy**: scope conversations and vectors via `tenant_id` in keys/metadata
- **Backups**: snapshot Postgres volume; persist Redis if needed (AOF enabled by default)
