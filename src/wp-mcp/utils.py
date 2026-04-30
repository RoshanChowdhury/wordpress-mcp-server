import os
import re
import httpx
from difflib import SequenceMatcher
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


async def get_categories() -> list[dict]:
    """Fetch all existing categories from WordPress."""
    try:
        async with _client() as client:
            response = await client.get(f"{WP_URL}/wp-json/wp/v2/categories", params={"per_page": 100})
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"WordPress API error {e.response.status_code}: {e.response.text}")
    except httpx.RequestError as e:
        raise RuntimeError(f"Failed to reach WordPress: {e}")


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _derive_keywords(title: str, content: str) -> list[str]:
    """Extract meaningful keywords from title and stripped content."""
    text = f"{title} {re.sub(r'<[^>]+>', ' ', content)}".lower()
    # remove common stop words and punctuation
    words = re.findall(r'[a-z]{4,}', text)
    stopwords = {"with", "this", "that", "from", "have", "will", "your", "their", "what", "when",
                 "which", "also", "into", "more", "than", "then", "them", "they", "been", "were",
                 "each", "make", "made", "some", "such", "like", "just", "over", "only", "both"}
    return [w for w in words if w not in stopwords]


async def _resolve_category(title: str, content: str) -> int:
    """
    Derive a category ID for the post:
    1. Extract keywords from title + content
    2. Try exact match against existing category names/slugs
    3. Try fuzzy match (similarity >= 0.6) against existing categories
    4. Only if no match found, create a new category derived from the title
    """
    existing = await get_categories()
    keywords = _derive_keywords(title, content)

    # 1. Exact keyword match against category name or slug
    for cat in existing:
        cat_name = cat["name"].lower()
        cat_slug = cat["slug"].lower()
        if any(kw == cat_name or kw == cat_slug or kw in cat_name or cat_name in kw for kw in keywords):
            return cat["id"]

    # 2. Fuzzy match — pick best scoring category above threshold
    best_id, best_score = None, 0.0
    combined = f"{title} {' '.join(keywords[:20])}"
    for cat in existing:
        score = max(_similarity(combined, cat["name"]), _similarity(combined, cat["slug"]))
        if score > best_score:
            best_score, best_id = score, cat["id"]

    if best_score >= 0.6 and best_id is not None:
        return best_id

    # 3. No match — create new category from the first meaningful title word
    new_name = title.strip().split()[0].capitalize() if title.strip() else "General"
    # avoid creating a duplicate with slightly different casing
    for cat in existing:
        if _similarity(new_name, cat["name"]) >= 0.85:
            return cat["id"]

    return await _create_category(new_name)


async def _create_category(name: str) -> int:
    try:
        async with _client() as client:
            response = await client.post(
                f"{WP_URL}/wp-json/wp/v2/categories",
                json={"name": name},
            )
            response.raise_for_status()
            return response.json()["id"]
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"WordPress API error {e.response.status_code}: {e.response.text}")
    except httpx.RequestError as e:
        raise RuntimeError(f"Failed to reach WordPress: {e}")


async def create_post(title: str, content: str, status: str = "draft") -> dict:
    category_id = await _resolve_category(title, content)
    try:
        async with _client() as client:
            response = await client.post(
                f"{WP_URL}/wp-json/wp/v2/posts",
                json={"title": title, "content": content, "status": status, "categories": [category_id]},
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
