import os
import httpx
from dotenv import load_dotenv

load_dotenv()

_REQUIRED = ("WP_URL", "WP_USER", "WP_PASS")
_missing = [v for v in _REQUIRED if not os.environ.get(v)]
if _missing:
    raise RuntimeError(f"Missing required environment variables: {', '.join(_missing)}")

WP_URL = os.environ["WP_URL"]
WP_USER = os.environ["WP_USER"]
WP_PASS = os.environ["WP_PASS"]
SSL_CERT = os.environ.get("WP_SSL_CERT", True)  # path to cert PEM, or True for system CAs


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(verify=SSL_CERT, auth=(WP_USER, WP_PASS))


async def get_posts(
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
    try:
        async with _client() as client:
            if post_id is not None:
                response = await client.get(f"{WP_URL}/wp-json/wp/v2/posts/{post_id}")
                response.raise_for_status()
                return response.json()
            params: dict = {"per_page": per_page, "page": page, "status": status, "orderby": orderby, "order": order}
            if search:
                params["search"] = search
            if author:
                params["author"] = author
            if categories:
                params["categories"] = ",".join(str(c) for c in categories)
            if tags:
                params["tags"] = ",".join(str(t) for t in tags)
            response = await client.get(f"{WP_URL}/wp-json/wp/v2/posts", params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"WordPress API error {e.response.status_code}: {e.response.text}")
    except httpx.RequestError as e:
        raise RuntimeError(f"Failed to reach WordPress: {e}")


async def create_post(title: str, content: str, status: str = "draft") -> dict:
    try:
        async with _client() as client:
            response = await client.post(
                f"{WP_URL}/wp-json/wp/v2/posts",
                json={"title": title, "content": content, "status": status},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"WordPress API error {e.response.status_code}: {e.response.text}")
    except httpx.RequestError as e:
        raise RuntimeError(f"Failed to reach WordPress: {e}")


async def update_post(post_id: int, title: str | None = None, content: str | None = None, status: str | None = None) -> dict:
    payload = {k: v for k, v in {"title": title, "content": content, "status": status}.items() if v is not None}
    try:
        async with _client() as client:
            response = await client.post(
                f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"WordPress API error {e.response.status_code}: {e.response.text}")
    except httpx.RequestError as e:
        raise RuntimeError(f"Failed to reach WordPress: {e}")


async def delete_post(post_id: int, force: bool = False) -> dict:
    try:
        async with _client() as client:
            response = await client.delete(
                f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
                params={"force": str(force).lower()},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"WordPress API error {e.response.status_code}: {e.response.text}")
    except httpx.RequestError as e:
        raise RuntimeError(f"Failed to reach WordPress: {e}")
