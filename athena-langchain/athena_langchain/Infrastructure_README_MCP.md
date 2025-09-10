MCP tooling in Athena-LangChain (quick start)

Environment (optional; defaults to a single stdio child process of our in-repo server):

```bash
export ATHENA_MCP_SERVERS='{
  "athena": {
    "command": "/usr/bin/python3",
    "args": ["-m", "athena_langchain.mcp.server"],
    "transport": "stdio"
  }
}'
```

At runtime, `athena_langchain.tools.merged_tools.get_merged_tools_sync()` returns:
- Local registry tools wrapped as LangChain BaseTools
- MCP tools fetched via langchain-mcp-adapters `MultiServerMCPClient`

Journaling agent is wired to LangGraph `ToolNode`, so tool calls are executed by LangGraph directly.


