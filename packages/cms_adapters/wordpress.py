"""WordPress CMS Adapter — connects via WordPress REST API.

Connection flow:
1. User provides WordPress site URL + Application Password (recommended) or JWT
2. test_connection() verifies with read-only GET /wp-json/wp/v2/users/me
3. Credentials encrypted and stored in sites.cms_token_encrypted
4. Fixes applied via PATCH to /wp-json/wp/v2/posts/:id or /pages/:id

Yoast SEO fields are updated via the _yoast_wpseo_title and
_yoast_wpseo_metadesc custom meta fields when Yoast is detected.
Rank Math fields are updated via rank_math_title and rank_math_description.
"""
from __future__ import annotations

import logging
from typing import Optional
from datetime import datetime

import httpx

from .base import BaseCMSAdapter, CMSPage, ApplyResult

log = logging.getLogger(__name__)


class WordPressAdapter(BaseCMSAdapter):
    """WordPress REST API adapter.

    Args:
        site_url: Base URL of the WordPress site (e.g. https://example.com)
        username: WordPress username (for Application Password auth)
        app_password: WordPress Application Password (recommended)
        jwt_token: Alternative JWT token (if Application Password not available)
    """

    def __init__(
        self,
        site_url: str,
        username: Optional[str] = None,
        app_password: Optional[str] = None,
        jwt_token: Optional[str] = None,
    ):
        self.site_url = site_url.rstrip("/")
        self.api_base = f"{self.site_url}/wp-json/wp/v2"
        self._username = username
        self._app_password = app_password
        self._jwt_token = jwt_token

    def _headers(self) -> dict:
        if self._jwt_token:
            return {"Authorization": f"Bearer {self._jwt_token}"}
        if self._username and self._app_password:
            import base64
            credentials = base64.b64encode(
                f"{self._username}:{self._app_password}".encode()
            ).decode()
            return {"Authorization": f"Basic {credentials}"}
        return {}

    async def _detect_seo_plugin(self, client: httpx.AsyncClient) -> str:
        """Detect which SEO plugin is active (yoast, rank_math, none)."""
        try:
            resp = await client.get(f"{self.api_base}/plugins", headers=self._headers())
            if resp.status_code == 200:
                plugins = resp.json()
                names = [p.get("plugin", "").lower() for p in plugins]
                if any("yoast" in n for n in names):
                    return "yoast"
                if any("rank-math" in n or "rankmath" in n for n in names):
                    return "rank_math"
        except Exception:
            pass
        return "none"

    async def test_connection(self) -> bool:
        """Read-only ping to verify credentials."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(
                    f"{self.api_base}/users/me",
                    headers=self._headers(),
                )
                return resp.status_code == 200
            except httpx.RequestError as exc:
                log.error("WordPress connection test failed: %s", exc)
                return False

    async def list_pages(self, limit: int = 500) -> list[CMSPage]:
        """Fetch all posts and pages from WordPress."""
        pages: list[CMSPage] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for endpoint in ("posts", "pages"):
                per_page = min(limit - len(pages), 100)
                page_num = 1
                while len(pages) < limit:
                    resp = await client.get(
                        f"{self.api_base}/{endpoint}",
                        params={"per_page": per_page, "page": page_num, "_fields": "id,link,title,meta,yoast_head_json"},
                        headers=self._headers(),
                    )
                    if resp.status_code != 200:
                        break
                    items = resp.json()
                    if not items:
                        break
                    for item in items:
                        pages.append(self._normalize(item))
                    if len(items) < per_page:
                        break
                    page_num += 1
        return pages[:limit]

    def _normalize(self, item: dict) -> CMSPage:
        yoast = item.get("yoast_head_json") or {}
        meta = item.get("meta") or {}
        return CMSPage(
            id=str(item.get("id", "")),
            url=item.get("link", ""),
            title=item.get("title", {}).get("rendered", "") if isinstance(item.get("title"), dict) else str(item.get("title", "")),
            meta_description=yoast.get("description") or meta.get("_yoast_wpseo_metadesc") or meta.get("rank_math_description", ""),
            canonical_url=yoast.get("canonical") or "",
            og_title=yoast.get("og_title") or "",
            og_description=yoast.get("og_description") or "",
            raw=item,
        )

    async def get_page(self, page_id: str) -> CMSPage:
        """Fetch a single page/post by ID."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            for endpoint in ("posts", "pages"):
                resp = await client.get(
                    f"{self.api_base}/{endpoint}/{page_id}",
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    return self._normalize(resp.json())
        raise ValueError(f"WordPress page {page_id} not found")

    async def apply_fix(self, page_id: str, field: str, new_value: str) -> ApplyResult:
        """Apply an approved SEO fix to WordPress.

        Supports updating: title, meta_description, og_title, og_description.
        Detects Yoast/Rank Math and writes to the correct meta fields.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            seo_plugin = await self._detect_seo_plugin(client)

            # Determine which endpoint (post or page) owns this ID
            resource_url: Optional[str] = None
            old_value: Optional[str] = None
            for endpoint in ("posts", "pages"):
                resp = await client.get(
                    f"{self.api_base}/{endpoint}/{page_id}",
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    resource_url = f"{self.api_base}/{endpoint}/{page_id}"
                    current = self._normalize(resp.json())
                    old_value = getattr(current, field, None)
                    break

            if not resource_url:
                return ApplyResult(success=False, message=f"Page {page_id} not found")

            # Build the update payload based on field and SEO plugin
            payload: dict = {}
            if field == "title":
                if seo_plugin == "yoast":
                    payload["meta"] = {"_yoast_wpseo_title": new_value}
                elif seo_plugin == "rank_math":
                    payload["meta"] = {"rank_math_title": new_value}
                else:
                    payload["title"] = new_value
            elif field == "meta_description":
                if seo_plugin == "yoast":
                    payload["meta"] = {"_yoast_wpseo_metadesc": new_value}
                elif seo_plugin == "rank_math":
                    payload["meta"] = {"rank_math_description": new_value}
                else:
                    payload["excerpt"] = {"raw": new_value}
            elif field == "og_title":
                payload["meta"] = {"_yoast_wpseo_opengraph-title": new_value}
            else:
                return ApplyResult(success=False, message=f"Unsupported field: {field}")

            resp = await client.patch(
                resource_url,
                json=payload,
                headers={**self._headers(), "Content-Type": "application/json"},
            )

            if resp.status_code in (200, 201):
                return ApplyResult(
                    success=True,
                    message=f"Updated {field} via WordPress REST API ({seo_plugin} plugin detected)",
                    rollback_value=old_value,
                    applied_at=datetime.utcnow().isoformat(),
                )
            else:
                return ApplyResult(
                    success=False,
                    message=f"WordPress API error {resp.status_code}: {resp.text[:200]}",
                )
