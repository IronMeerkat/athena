"""
MCP client initialization and tool aggregation.
"""
import asyncio
from typing import Any, List

from athena_logging import get_logger
from athena_settings import settings
from langchain.retrievers import ContextualCompressionRetriever
from langchain.tools.retriever import create_retriever_tool
from langchain_core.tools import BaseTool
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_mcp_adapters.client import MultiServerMCPClient

from utils.build_retriever import build_retriever
from utils import vectorstore
from .memory import memory_tools
from .finance import call_finance_agent

logger = get_logger(__name__)

async def initialize_mcp_client():
    """Initialize the MCP multi-server client and return tools."""
    try:
        ergane = MultiServerMCPClient(
            {
                # "ergane": settings.ERGANE_CONFIGURATIONS.model_dump(),
                "Notion": {
                "command": "npx",
                "transport": "stdio",
                "args": ["-y", "@notionhq/notion-mcp-server", "--transport", "stdio"],
                "env": {
                    "NOTION_TOKEN": settings.NOTION_API_KEY
                    },
                },
                "playwright": {
                    "transport": "stdio",
                    "command": "npx",
                    "args": ["-y", "@playwright/mcp@latest", "--headless", "--browser", "chromium", "--no-sandbox"],
                },
                # "zapier": {
                #     "transport": "streamable_http",
                #     "url": settings.ZAPIER_URL
                # },
            }
        )

        mcp_tools = await ergane.get_tools()
        logger.info(f"Initialized MCP client with {len(mcp_tools)} tools")

        return ergane, mcp_tools
    except Exception as e:
        logger.exception("Failed to initialize MCP client")
        return None, []

def create_rag_tool(vectorstore) -> BaseTool:
    """Create the RAG retrieval tool."""
    try:
        retriever: VectorStoreRetriever | ContextualCompressionRetriever = build_retriever(vectorstore)
        rag_tool = create_retriever_tool(
            retriever,
            name="search_docs",
            description="Retrieve and rerank relevant context from the RAG vector store.",
        )
        logger.info("Created RAG tool successfully")
        return rag_tool
    except Exception as e:
        logger.exception("Failed to create RAG tool")
        return None

async def get_all_tools(vectorstore) -> tuple[List[BaseTool], Any]:
    """
    Get all tools including MCP tools, RAG tool, and memory tools.

    Returns:
        tuple: (tools_list, ergane_client)
    """
    try:
        # Initialize MCP client and get tools
        ergane, mcp_tools = await initialize_mcp_client()

        # Start with MCP tools
        all_tools = mcp_tools if mcp_tools else []

        # Add RAG tool
        rag_tool = create_rag_tool(vectorstore)
        if rag_tool:
            all_tools.append(rag_tool)

        # Add memory tools
        all_tools.extend(memory_tools)

        # Add finance tool
        all_tools.append(call_finance_agent)

        logger.info(f"Aggregated {len(all_tools)} total tools")
        return all_tools, ergane

    except Exception as e:
        logger.exception("Failed to aggregate tools")
        return [], None


tools, ergane = asyncio.run(get_all_tools(vectorstore))