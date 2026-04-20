"""AutoSEO Crawler package — 4-layer crawl architecture."""
from .robots import get_robots_rules, is_allowed, get_crawl_delay
from .sitemap import discover_sitemap_urls
from .extractor import SEOExtractor, calculate_page_score, generate_issues

__all__ = [
    "get_robots_rules",
    "is_allowed",
    "get_crawl_delay",
    "discover_sitemap_urls",
    "SEOExtractor",
    "calculate_page_score",
    "generate_issues",
]
