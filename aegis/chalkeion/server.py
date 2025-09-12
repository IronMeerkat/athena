import asyncio
import nest_asyncio
import sys

nest_asyncio.apply()

from athena_logging import get_logger

logger = get_logger(__name__)

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("chalkeion", debug=True)

@mcp.tool()
def add(a: int, b: int) -> int:
    logger.info(f"Fake adding {a} and {b}")
    return a / b

if not any(cmd in sys.argv for cmd in ("migrate", "makemigrations", "collectstatic")):

    mcp.run(transport="stdio")