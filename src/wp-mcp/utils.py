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


async def get_posts(per_page: int = 5) -> list:
    try:
        async with httpx.AsyncClient(verify=SSL_CERT) as client:
            response = await client.get(
                f"{WP_URL}/wp-json/wp/v2/posts",
                params={"per_page": per_page, "orderby": "date", "order": "desc"},
                auth=(WP_USER, WP_PASS),
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"WordPress API error {e.response.status_code}: {e.response.text}")
    except httpx.RequestError as e:
        raise RuntimeError(f"Failed to reach WordPress: {e}")
