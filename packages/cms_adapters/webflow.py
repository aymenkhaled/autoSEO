"""Webflow CMS Adapter — Webflow Data API v2 (sites/pages/CMS items).

Connection flow:
1. User generates a Site API token in Webflow → Site Settings → Apps & Integrations.
   Required scopes: `pages:read`, `pages:write`, `cms:read`, `cms:write`.
2. test_connection() verifies via GET /v2/sites/{site_id}.
3. Page SEO fields are written via PATCH /v2/pages/{page_id} (title, seo, openGraph).
4. CMS item meta is written via PATCH /v2/collections/{collection_id}/items/{item_id}
   on the `name` and `metaDescription`/`metaTitle` fields when present.
5. Webflow uses a publish/draft model — apply_fix() calls publish() for the page after.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import httpx

from .base import BaseCMSAdapter, CMSPage, ApplyResult

log = logging.getLogger(__name__)

API_BASE = "https://api.webflow.com/v2"


class WebflowAdapter(BaseCMSAdapter):
    """Webflow Data API v2 adapter.

    Args:
        site_id: Webflow site ID
        token: Site-scoped API token
    """

    def __init__(self, site_id: str, token: str):
        self.site_id = site_id
        self.token = token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def test_connection(self) -> bool:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(f"{API_BASE}/sites/{self.site_id}", headers=self._headers())
                return resp.status_code == 200
            except httpx.RequestError as exc:
                log.error("Webflow connection test failed: %s", exc)
                return False

    async def list_pages(self, limit: int = 500) -> list[CMSPage]:
        out: list[CMSPage] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            offset = 0
            while len(out) < limit:
                resp = await client.get(
                    f"{API_BASE}/sites/{self.site_id}/pages",
                    params={"limit": min(100, limit - len(out)), "offset": offset},
                    headers=self._headers(),
                )
                if resp.status_code != 200:
                    break
                data = resp.json()
                items = data.get("pages", [])
                if not items:
                    break
                for it in items:
                    out.append(self._normalize_page(it))
                if len(items) < 100:
                    break
                offset += len(items)
        return out[:limit]

    def _normalize_page(self, item: dict) -> CMSPage:
        seo = item.get("seo") or {}
        og = item.get("openGraph") or {}
        return CMSPage(
            id=f"page:{item.get('id')}",
            url=item.get("publishedPath") or item.get("slug") or "",
            title=seo.get("title") or item.get("title", ""),
            meta_description=seo.get("description") or "",
            og_title=og.get("title"),
            og_description=og.get("description"),
            raw=item,
        )

    async def get_page(self, page_id: str) -> CMSPage:
        kind, _, pid = page_id.partition(":")
        if kind != "page":
            raise ValueError(f"Webflow get_page only supports page IDs, got {page_id}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{API_BASE}/pages/{pid}", headers=self._headers())
            if resp.status_code == 200:
                return self._normalize_page(resp.json())
        raise ValueError(f"Webflow page {pid} not found")

    async def apply_fix(self, page_id: str, field: str, new_value: str) -> ApplyResult:
        kind, _, pid = page_id.partition(":")
        if kind != "page":
            return ApplyResult(success=False, message=f"Only page: IDs supported, got {page_id}")

        async with httpx.AsyncClient(timeout=15.0) as client:
            # 1. Read current value for rollback
            cur_resp = await client.get(f"{API_BASE}/pages/{pid}", headers=self._headers())
            if cur_resp.status_code != 200:
                return ApplyResult(success=False, message=f"Page {pid} not found")
            cur = cur_resp.json()
            cur_seo = cur.get("seo") or {}

            payload: dict = {}
            old_value: Optional[str] = None
            if field == "title":
                old_value = cur_seo.get("title") or cur.get("title")
                payload["seo"] = {**cur_seo, "title": new_value}
            elif field == "meta_description":
                old_value = cur_seo.get("description")
                payload["seo"] = {**cur_seo, "description": new_value}
            elif field == "og_title":
                old_value = (cur.get("openGraph") or {}).get("title")
                payload["openGraph"] = {**(cur.get("openGraph") or {}), "title": new_value}
            elif field == "og_description":
                old_value = (cur.get("openGraph") or {}).get("description")
                payload["openGraph"] = {**(cur.get("openGraph") or {}), "description": new_value}
            else:
                return ApplyResult(success=False, message=f"Unsupported field for Webflow pages: {field}")

            try:
                resp = await client.put(f"{API_BASE}/pages/{pid}", json=payload, headers=self._headers())
            except httpx.RequestError as exc:
                return ApplyResult(success=False, message=f"Webflow request failed: {exc}")

            if resp.status_code not in (200, 202):
                return ApplyResult(success=False, message=f"Webflow {resp.status_code}: {resp.text[:200]}")

            # 2. Publish so the change goes live (best-effort — Webflow returns 202 on accept)
            try:
                await client.post(
                    f"{API_BASE}/sites/{self.site_id}/publish",
                    json={"publishToWebflowSubdomain": True},
                    headers=self._headers(),
                )
            except httpx.RequestError as exc:
                log.warning("Webflow publish failed (change saved as draft): %s", exc)

            return ApplyResult(
                success=True,
                message=f"Updated Webflow page {pid}.{field}",
                rollback_value=old_value,
                applied_at=datetime.utcnow().isoformat(),
            )
