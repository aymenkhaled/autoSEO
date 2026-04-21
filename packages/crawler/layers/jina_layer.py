"""Layer 1 — Jina AI Reader: fast HTML-to-markdown for static sites."""
import os
import time
import httpx


async def fetch_with_jina(url: str) -> dict | None:
    """Fetch a URL via Jina Reader. Returns html+headers+status or None on failure."""
    jina_url = f"https://r.jina.ai/{url}"
    headers = {
        "Accept": "application/json",
        "X-Return-Format": "html",
        "X-With-Links-Summary": "true",
        "X-With-Images-Summary": "true",
    }
    api_key = os.environ.get("JINA_API_KEY", "")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    started = time.perf_counter()
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        try:
            resp = await client.get(jina_url, headers=headers)
            elapsed_ms = int((time.perf_counter() - started) * 1000)

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    content_data = data.get("data", {}) if isinstance(data, dict) else {}
                except Exception:
                    content_data = {}

                # Jina returns target's effective status in metadata when available
                target_status = 200
                target_headers: dict[str, str] = {}
                if isinstance(content_data, dict):
                    meta = content_data.get("metadata") or {}
                    if isinstance(meta, dict):
                        target_status = int(meta.get("statusCode") or 200)
                        if isinstance(meta.get("headers"), dict):
                            target_headers = {
                                str(k).lower(): str(v) for k, v in meta["headers"].items()
                            }

                return {
                    "url": url,
                    "html": content_data.get("html") or content_data.get("content") or "",
                    "content": content_data.get("content", ""),
                    "title": content_data.get("title", ""),
                    "status_code": target_status,
                    "headers": target_headers,
                    "response_time_ms": elapsed_ms,
                    "source": "jina",
                }

            # Surface non-200 so the orchestrator can record the broken URL
            return {
                "url": url,
                "html": "",
                "status_code": resp.status_code,
                "headers": {},
                "response_time_ms": elapsed_ms,
                "source": "jina",
            }
        except Exception:
            return None
