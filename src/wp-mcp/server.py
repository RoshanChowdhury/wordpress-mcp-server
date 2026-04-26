import os
from typing import Literal
from mcp.server.fastmcp import FastMCP
from utils import get_posts

Transport = Literal["stdio", "sse", "streamable-http"]
transport: Transport = os.environ.get("MCP_TRANSPORT", "stdio")  # type: ignore[assignment]
port = int(os.environ.get("PORT", "8080"))

mcp = FastMCP("WP-Actions")


@mcp.tool()
async def get_latest_posts() -> list:
    """Get the latest 5 posts from WordPress."""
    return await get_posts(per_page=5)


if __name__ == "__main__":
    if transport == "streamable-http":
        mcp.run(transport=transport, host="0.0.0.0", port=port)
    else:
        mcp.run(transport=transport)
