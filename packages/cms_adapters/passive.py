"""Passive CMS adapters — for connection types that don't expose a write API.

These exist so the factory can return SOMETHING for every supported
connection_type, and so the apply pipeline returns a clean message
("manual fix required") instead of a 500 error.

  • CrawlerAdapter — the site is monitored read-only via crawling
  • SnippetAdapter — fixes are pushed to the page via the JS snippet at runtime
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from .base import BaseCMSAdapter, CMSPage, ApplyResult


class CrawlerAdapter(BaseCMSAdapter):
    """Read-only adapter — used when the user picked 'crawler' (no CMS connected).

    The crawler can detect issues and the AI can suggest fixes, but the user
    must apply them manually because we have no write surface.
    """

    def __init__(self, domain: str | None = None):
        self.domain = domain

    async def test_connection(self) -> bool:
        return True  # crawler is always "connected"

    async def list_pages(self, limit: int = 500) -> list[CMSPage]:
        return []

    async def get_page(self, page_id: str) -> CMSPage:
        raise NotImplementedError("Crawler adapter does not support get_page — pages live in the database")

    async def apply_fix(self, page_id: str, field: str, new_value: str) -> ApplyResult:
        return ApplyResult(
            success=False,
            message=(
                "This site is monitored via crawling only — connect WordPress, Shopify, "
                "Webflow, GitHub, or install the snippet to enable one-click fixes."
            ),
        )


class SnippetAdapter(BaseCMSAdapter):
    """Snippet-based adapter used for read-only monitoring/install guidance."""

    def __init__(self, site_token: str | None = None):
        self.site_token = site_token

    async def test_connection(self) -> bool:
        return bool(self.site_token)

    async def list_pages(self, limit: int = 500) -> list[CMSPage]:
        return []

    async def get_page(self, page_id: str) -> CMSPage:
        raise NotImplementedError("Snippet adapter does not support get_page")

    async def apply_fix(self, page_id: str, field: str, new_value: str) -> ApplyResult:
        return ApplyResult(
            success=False,
            message="Snippet mode currently collects live SEO data but does not auto-deploy fixes.",
        )
