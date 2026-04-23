"""robots.txt parser and compliance checker.

Gap 2 (deferred → done): in-process cache so a single domain's robots.txt
is fetched once and reused across every page in the same crawl process.
"""
import time
import httpx
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse

from packages.crawler.url_utils import is_safe_url


# Module-level cache: { (host, user_agent): (parser, fetched_at_unix) }
_CACHE: dict[tuple[str, str], tuple[RobotFileParser, float]] = {}
_CACHE_TTL_SECONDS = 3600  # 1 hour


def _host_key(domain: str) -> str:
    parsed = urlparse(domain if domain.startswith("http") else f"https://{domain}")
    return f"{parsed.scheme}://{parsed.netloc}".lower()


async def get_robots_rules(domain: str, user_agent: str = "AutoSEO") -> RobotFileParser:
    """Fetch & parse robots.txt for a domain. Cached per (host, user_agent)."""
    key = (_host_key(domain), user_agent)
    now = time.time()

    cached = _CACHE.get(key)
    if cached and (now - cached[1]) < _CACHE_TTL_SECONDS:
        return cached[0]

    robots_url = urljoin(_host_key(domain) + "/", "robots.txt")
    if not is_safe_url(robots_url):
        return parser
    parser = RobotFileParser()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(robots_url, timeout=10)
            if resp.status_code == 200 and is_safe_url(str(resp.url)):
                parser.parse(resp.text.splitlines())
    except Exception:
        # Empty parser → allows everything by default
        pass

    _CACHE[key] = (parser, now)
    return parser


def clear_robots_cache() -> None:
    """Test/debug helper."""
    _CACHE.clear()


def is_allowed(parser: RobotFileParser, url: str, user_agent: str = "AutoSEO") -> bool:
    return parser.can_fetch(user_agent, url)


def get_crawl_delay(parser: RobotFileParser, user_agent: str = "AutoSEO") -> float:
    delay = parser.crawl_delay(user_agent)
    return max(delay or 1.0, 1.0)
