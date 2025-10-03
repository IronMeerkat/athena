import asyncio
import sys
from typing import List, Dict, Any, Optional

from athena_logging import get_logger
from athena_settings import settings
from athena_models import Prompt, PromptRole, db_session
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
import sqlalchemy as sa
from prompts import all_prompt_tools
from tools import call_finance_agent


logger = get_logger(__name__)

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ergane", debug=True)

# for tool in all_prompt_tools:
#     # Register both async and sync tools directly with MCP
#     mcp.tool()(tool)

mcp.tool()(call_finance_agent)

logger.info("Running MCP server on stdio")
asyncio.run(mcp.run_stdio_async())

