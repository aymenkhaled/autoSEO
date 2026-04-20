"""Layer 3 — ScrapFly: commercial anti-bot bypass for protected sites."""
import os
from typing import Optional

BLOCKED_SIGNALS = [
    "Just a moment",
    "Checking your browser",
    "cf-browser-verification",
    "DDoS protection by Cloudflare",
    "datadome",
    "Access denied",
]


def is_blocked(html: str) -> bool:
    html_lower = html.lower()
    return any(s.lower() in html_lower for s in BLOCKED_SIGNALS)


async def fetch_with_scrapfly(url: str) -> Optional[dict]:
    api_key = os.environ.get("SCRAPFLY_API_KEY", "")
    if not api_key:
        return None

    try:
        from scrapfly import ScrapflyClient, ScrapeConfig
        client = ScrapflyClient(key=api_key)
        result = await client.async_scrape(ScrapeConfig(
            url=url,
            asp=True,
            render_js=True,
            rendering_wait=2000,
            country="US",
            retry=False,
        ))
        if result.upstream_status_code == 200:
            return {
                "url": url,
                "html": result.scrape_result["content"],
                "status_code": 200,
                "source": "scrapfly",
            }
    except ImportError:
        pass
    except Exception:
        pass
    return None
