"""Layer 1 — Jina AI Reader: fast HTML-to-markdown for static sites."""
import httpx


async def fetch_with_jina(url: str) -> dict | None:
    jina_url = f"https://r.jina.ai/{url}"
    headers = {
        "Accept": "application/json",
        "X-Return-Format": "markdown",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(jina_url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                content_data = data.get("data", {})
                return {
                    "content": content_data.get("content", ""),
                    "title": content_data.get("title", ""),
                    "html": content_data.get("html", ""),
                    "url": url,
                    "source": "jina",
                    "status_code": 200,
                }
        except Exception:
            pass
    return None
