import os
from typing import Literal
from mcp.server.fastmcp import FastMCP
from utils import get_posts, get_categories, create_post, update_post, delete_post

Transport = Literal["stdio", "sse", "streamable-http"]
transport: Transport = os.environ.get("MCP_TRANSPORT", "stdio")  # type: ignore[assignment]
port = int(os.environ.get("PORT", "8080"))

mcp = FastMCP("WP-Actions", host="0.0.0.0", port=port)


@mcp.tool()
async def get_latest_posts(per_page: int = 5) -> list:
    """Get the latest 5 posts from WordPress.Defaults to 5."""
    return await get_posts(per_page)


@mcp.tool()
async def fetch_posts(
    per_page: int = 5,
    page: int = 1,
    search: str | None = None,
    status: str = "publish",
    orderby: str = "date",
    order: str = "desc",
    author: int | None = None,
    categories: list[int] | None = None,
    tags: list[int] | None = None,
    post_id: int | None = None,
) -> list | dict:
    """
    Generic tool to fetch WordPress posts with filters.
    - post_id: fetch a single post by ID
    - search: keyword search
    - status: 'publish', 'draft', 'any', etc.
    - orderby: 'date', 'title', 'id', etc.
    - order: 'asc' or 'desc'
    - per_page / page: pagination
    - author: filter by author ID
    - categories / tags: filter by list of category or tag IDs
    """
    return await get_posts(per_page, page, search, status, orderby, order, author, categories, tags, post_id)


@mcp.tool()
async def get_post_categories() -> list:
    """Fetch all existing categories from WordPress."""
    return await get_categories()


@mcp.tool()
async def create_new_post(title: str, content: str, status: str = "draft") -> dict:
    """Create a new WordPress post. Automatically derives and assigns a category based on content. status to be 'draft' or 'publish'."""
    return await create_post(title, content, status)


@mcp.tool()
async def update_existing_post(post_id: int, title: str | None = None, content: str | None = None, status: str | None = None) -> dict:
    """Update an existing WordPress post by ID. Only provided fields are updated."""
    return await update_post(post_id, title, content, status)


@mcp.tool()
async def delete_existing_post(post_id: int, force: bool = False) -> dict:
    """Delete a WordPress post by ID. Set force=True to permanently delete (bypass trash)."""
    return await delete_post(post_id, force)


if __name__ == "__main__":
    mcp.run(transport=transport)
