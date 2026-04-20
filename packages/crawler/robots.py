"""robots.txt parser and compliance checker."""
import httpx
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin


async def get_robots_rules(domain: str, user_agent: str = "AutoSEO") -> RobotFileParser:
    robots_url = urljoin(domain, "/robots.txt")
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(robots_url, timeout=10)
            parser = RobotFileParser()
            parser.parse(resp.text.splitlines())
            return parser
        except Exception:
            return RobotFileParser()


def is_allowed(parser: RobotFileParser, url: str, user_agent: str = "AutoSEO") -> bool:
    return parser.can_fetch(user_agent, url)


def get_crawl_delay(parser: RobotFileParser, user_agent: str = "AutoSEO") -> float:
    delay = parser.crawl_delay(user_agent)
    return max(delay or 1.0, 1.0)
