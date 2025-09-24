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

logger = get_logger(__name__)

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ergane", debug=True)

def async_tool(func):

    return mcp.tool()(asyncio.run(func))

for tool in all_prompt_tools:
    if asyncio.iscoroutinefunction(tool):
        tool = async_tool(tool)
    else:
        tool = mcp.tool()(tool)



asyncio.run(mcp.run_stdio_async())

