import os
from mcp.server.fastmcp import FastMCP
from utils import get_posts

from typing import Literal

Transport = Literal["stdio", "sse", "streamable-http"]
transport: Transport = os.environ.get("MCP_TRANSPORT", "stdio")  # type: ignore[assignment]

mcp = FastMCP(
    "WP-Actions",
    **(dict(host="0.0.0.0", port=8080) if transport == "sse" else {}),
)


@mcp.tool()
async def get_latest_posts() -> list:
    """Get the latest 5 posts from WordPress."""
    return await get_posts(per_page=5)


if __name__ == "__main__":
    mcp.run(transport=transport)
