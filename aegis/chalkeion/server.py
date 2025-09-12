import asyncio
import nest_asyncio

nest_asyncio.apply()

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("chalkeion")

@mcp.tool()
def add(a: int, b: int) -> int:
    return a + b

if __name__ == "__main__":
    mcp.run(transport="stdio")  # blocks, manages asyncio internally