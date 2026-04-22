"""CMS Adapters package — factory and exports.

Supported connection types:
    crawler   → CrawlerAdapter   (read-only; no write surface)
    snippet   → SnippetAdapter   (write via runtime JS injection)
    wordpress → WordPressAdapter (REST API + Yoast/Rank Math)
    shopify   → ShopifyAdapter   (Admin REST API 2024-10)
    webflow   → WebflowAdapter   (Data API v2)
    github    → GitHubAdapter    (PR-based fixes for Astro/Next/Hugo/Jekyll)
"""
from .base import BaseCMSAdapter, CMSPage, ApplyResult
from .wordpress import WordPressAdapter
from .github_adapter import GitHubAdapter
from .shopify import ShopifyAdapter
from .webflow import WebflowAdapter
from .passive import CrawlerAdapter, SnippetAdapter


_ADAPTERS = {
    "crawler": CrawlerAdapter,
    "snippet": SnippetAdapter,
    "wordpress": WordPressAdapter,
    "shopify": ShopifyAdapter,
    "webflow": WebflowAdapter,
    "github": GitHubAdapter,
}


def get_adapter(connection_type: str, **kwargs) -> BaseCMSAdapter:
    """Factory — returns the correct adapter for the given CMS type.

    kwargs are forwarded to the adapter constructor, e.g.:
      get_adapter("wordpress", site_url=..., username=..., app_password=...)
      get_adapter("shopify", shop_domain=..., access_token=...)
      get_adapter("webflow", site_id=..., token=...)
      get_adapter("github", owner=..., repo=..., token=..., branch="main")
    """
    cls = _ADAPTERS.get(connection_type)
    if cls is None:
        raise ValueError(
            f"Unknown connection type '{connection_type}'. "
            f"Supported: {list(_ADAPTERS.keys())}"
        )
    return cls(**kwargs)


def supported_connection_types() -> list[str]:
    return list(_ADAPTERS.keys())


__all__ = [
    "BaseCMSAdapter", "CMSPage", "ApplyResult",
    "WordPressAdapter", "GitHubAdapter", "ShopifyAdapter",
    "WebflowAdapter", "CrawlerAdapter", "SnippetAdapter",
    "get_adapter", "supported_connection_types",
]
