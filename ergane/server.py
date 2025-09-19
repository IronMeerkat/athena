import asyncio
import sys


from athena_logging import get_logger
from athena_settings import settings

logger = get_logger(__name__)

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ergane", debug=True)

@mcp.tool()
def add(a: int, b: int) -> int:
    logger.info(f"Fake adding {a} and {b}")
    return a / b


asyncio.run(mcp.run_stdio_async())

