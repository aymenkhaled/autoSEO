"""CMS Adapter Base Class — defines the interface all adapters must implement."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class CMSPage:
    """Normalized page representation returned by all adapters."""
    id: str
    url: str
    title: str
    meta_description: str
    meta_keywords: Optional[str] = None
    canonical_url: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    raw: Optional[dict] = None


@dataclass
class ApplyResult:
    success: bool
    message: str
    rollback_value: Optional[str] = None
    applied_at: Optional[str] = None


class BaseCMSAdapter(ABC):
    """Abstract base for all CMS adapters.

    Each adapter must:
    1. Implement test_connection() — read-only ping before storing credentials
    2. Implement get_page() — fetch a single page's SEO data
    3. Implement apply_fix() — write an approved fix back to the CMS
    4. Implement list_pages() — return all crawlable pages

    Adapters must NEVER write to production until apply_fix() is explicitly called.
    """

    @abstractmethod
    async def test_connection(self) -> bool:
        """Verify credentials with a read-only API call. Must not write anything."""
        ...

    @abstractmethod
    async def list_pages(self, limit: int = 500) -> list[CMSPage]:
        """Return all pages/posts available in this CMS."""
        ...

    @abstractmethod
    async def get_page(self, page_id: str) -> CMSPage:
        """Fetch current SEO fields for a single page."""
        ...

    @abstractmethod
    async def apply_fix(
        self,
        page_id: str,
        field: str,
        new_value: str,
    ) -> ApplyResult:
        """Write an approved fix to the CMS.

        Args:
            page_id: CMS-specific page identifier
            field: Field to update (title, meta_description, alt_text, etc.)
            new_value: The AI-generated replacement value

        Returns:
            ApplyResult with success flag and the old value for rollback
        """
        ...
