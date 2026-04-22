"""Shopify CMS Adapter — connects via the Shopify Admin REST API.

Connection flow:
1. User installs an Admin API access token (from a custom app in Shopify Admin)
   with scopes: read_products, write_products, read_content, write_content,
   read_online_store_pages, write_online_store_pages.
2. test_connection() verifies via GET /shop.json.
3. SEO fields are written via PUT /products/:id.json (metafields_global_title_tag
   and metafields_global_description_tag) and PUT /pages/:id.json.
4. Blog articles are supported via /blogs/:blog_id/articles/:id.json.

Uses Admin API version 2024-10 (LTS-stable).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import httpx

from .base import BaseCMSAdapter, CMSPage, ApplyResult

log = logging.getLogger(__name__)

API_VERSION = "2024-10"


class ShopifyAdapter(BaseCMSAdapter):
    """Shopify Admin REST API adapter.

    Args:
        shop_domain: e.g. "mystore.myshopify.com"  (no scheme)
        access_token: Admin API access token from a custom app
    """

    def __init__(self, shop_domain: str, access_token: str):
        d = (shop_domain or "").strip().lower()
        d = d.replace("https://", "").replace("http://", "").rstrip("/")
        self.shop_domain = d
        self.access_token = access_token
        self.api_base = f"https://{self.shop_domain}/admin/api/{API_VERSION}"

    def _headers(self) -> dict:
        return {
            "X-Shopify-Access-Token": self.access_token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def test_connection(self) -> bool:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(f"{self.api_base}/shop.json", headers=self._headers())
                return resp.status_code == 200
            except httpx.RequestError as exc:
                log.error("Shopify connection test failed: %s", exc)
                return False

    async def list_pages(self, limit: int = 500) -> list[CMSPage]:
        """List products + pages + blog articles, normalized into CMSPage.

        page_id format encodes resource type so apply_fix can route correctly:
            product:<id>      → products
            page:<id>         → online-store pages
            article:<blog>:<id> → blog articles
        """
        out: list[CMSPage] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Products
            cursor = None
            while len(out) < limit:
                params = {"limit": min(250, limit - len(out)), "fields": "id,title,handle,body_html,metafields_global_title_tag,metafields_global_description_tag"}
                if cursor:
                    params["page_info"] = cursor
                resp = await client.get(f"{self.api_base}/products.json", params=params, headers=self._headers())
                if resp.status_code != 200:
                    break
                items = resp.json().get("products", [])
                if not items:
                    break
                for it in items:
                    out.append(self._normalize_product(it))
                # Cursor pagination via Link header
                cursor = _parse_next_cursor(resp.headers.get("link"))
                if not cursor:
                    break

            # Online-store pages
            if len(out) < limit:
                resp = await client.get(
                    f"{self.api_base}/pages.json",
                    params={"limit": min(250, limit - len(out))},
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    for it in resp.json().get("pages", []):
                        out.append(self._normalize_page(it))

        return out[:limit]

    def _public_url(self, slug: str, kind: str) -> str:
        if kind == "product":
            return f"https://{self.shop_domain}/products/{slug}"
        if kind == "page":
            return f"https://{self.shop_domain}/pages/{slug}"
        return f"https://{self.shop_domain}/{slug}"

    def _normalize_product(self, item: dict) -> CMSPage:
        return CMSPage(
            id=f"product:{item['id']}",
            url=self._public_url(item.get("handle", ""), "product"),
            title=item.get("metafields_global_title_tag") or item.get("title", ""),
            meta_description=item.get("metafields_global_description_tag") or "",
            raw=item,
        )

    def _normalize_page(self, item: dict) -> CMSPage:
        return CMSPage(
            id=f"page:{item['id']}",
            url=self._public_url(item.get("handle", ""), "page"),
            title=item.get("title", ""),
            meta_description="",
            raw=item,
        )

    async def get_page(self, page_id: str) -> CMSPage:
        kind, _, rest = page_id.partition(":")
        async with httpx.AsyncClient(timeout=10.0) as client:
            if kind == "product":
                resp = await client.get(f"{self.api_base}/products/{rest}.json", headers=self._headers())
                if resp.status_code == 200:
                    return self._normalize_product(resp.json().get("product", {}))
            elif kind == "page":
                resp = await client.get(f"{self.api_base}/pages/{rest}.json", headers=self._headers())
                if resp.status_code == 200:
                    return self._normalize_page(resp.json().get("page", {}))
            elif kind == "article":
                blog_id, _, art_id = rest.partition(":")
                resp = await client.get(
                    f"{self.api_base}/blogs/{blog_id}/articles/{art_id}.json",
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    art = resp.json().get("article", {})
                    return CMSPage(
                        id=page_id,
                        url=self._public_url(art.get("handle", ""), "article"),
                        title=art.get("title", ""),
                        meta_description=art.get("summary_html", "") or "",
                        raw=art,
                    )
        raise ValueError(f"Shopify resource {page_id} not found")

    async def apply_fix(self, page_id: str, field: str, new_value: str) -> ApplyResult:
        kind, _, rest = page_id.partition(":")
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                if kind == "product":
                    return await self._update_product(client, rest, field, new_value)
                if kind == "page":
                    return await self._update_page(client, rest, field, new_value)
                if kind == "article":
                    blog_id, _, art_id = rest.partition(":")
                    return await self._update_article(client, blog_id, art_id, field, new_value)
            except httpx.RequestError as exc:
                return ApplyResult(success=False, message=f"Shopify request failed: {exc}")
        return ApplyResult(success=False, message=f"Unsupported page_id: {page_id}")

    async def _update_product(self, client: httpx.AsyncClient, pid: str, field: str, new_value: str) -> ApplyResult:
        # Read current value first (rollback target)
        cur_resp = await client.get(f"{self.api_base}/products/{pid}.json", headers=self._headers())
        if cur_resp.status_code != 200:
            return ApplyResult(success=False, message=f"Product {pid} not found")
        cur = cur_resp.json().get("product", {})

        payload: dict = {"product": {"id": int(pid)}}
        old_value: Optional[str] = None
        if field == "title":
            old_value = cur.get("metafields_global_title_tag") or cur.get("title")
            payload["product"]["metafields_global_title_tag"] = new_value
        elif field == "meta_description":
            old_value = cur.get("metafields_global_description_tag")
            payload["product"]["metafields_global_description_tag"] = new_value
        else:
            return ApplyResult(success=False, message=f"Unsupported field for products: {field}")

        resp = await client.put(f"{self.api_base}/products/{pid}.json", json=payload, headers=self._headers())
        if resp.status_code in (200, 201):
            return ApplyResult(
                success=True,
                message=f"Updated product {pid}.{field}",
                rollback_value=old_value,
                applied_at=datetime.utcnow().isoformat(),
            )
        return ApplyResult(success=False, message=f"Shopify {resp.status_code}: {resp.text[:200]}")

    async def _update_page(self, client: httpx.AsyncClient, pid: str, field: str, new_value: str) -> ApplyResult:
        cur_resp = await client.get(f"{self.api_base}/pages/{pid}.json", headers=self._headers())
        if cur_resp.status_code != 200:
            return ApplyResult(success=False, message=f"Page {pid} not found")
        cur = cur_resp.json().get("page", {})

        payload: dict = {"page": {"id": int(pid)}}
        old_value: Optional[str] = None
        if field == "title":
            old_value = cur.get("title")
            payload["page"]["title"] = new_value
        elif field == "meta_description":
            # Online-store pages don't have a first-class meta description field —
            # use a metafield in the global namespace.
            mf_payload = {
                "metafield": {
                    "namespace": "global",
                    "key": "description_tag",
                    "value": new_value,
                    "type": "single_line_text_field",
                }
            }
            mf_resp = await client.post(
                f"{self.api_base}/pages/{pid}/metafields.json",
                json=mf_payload,
                headers=self._headers(),
            )
            if mf_resp.status_code in (200, 201):
                return ApplyResult(success=True, message="Page meta description metafield set", rollback_value="")
            return ApplyResult(success=False, message=f"Shopify {mf_resp.status_code}: {mf_resp.text[:200]}")
        else:
            return ApplyResult(success=False, message=f"Unsupported field for pages: {field}")

        resp = await client.put(f"{self.api_base}/pages/{pid}.json", json=payload, headers=self._headers())
        if resp.status_code in (200, 201):
            return ApplyResult(
                success=True, message=f"Updated page {pid}.{field}",
                rollback_value=old_value, applied_at=datetime.utcnow().isoformat(),
            )
        return ApplyResult(success=False, message=f"Shopify {resp.status_code}: {resp.text[:200]}")

    async def _update_article(
        self, client: httpx.AsyncClient, blog_id: str, art_id: str, field: str, new_value: str,
    ) -> ApplyResult:
        cur_resp = await client.get(
            f"{self.api_base}/blogs/{blog_id}/articles/{art_id}.json",
            headers=self._headers(),
        )
        if cur_resp.status_code != 200:
            return ApplyResult(success=False, message=f"Article {art_id} not found")
        cur = cur_resp.json().get("article", {})

        payload: dict = {"article": {"id": int(art_id)}}
        old_value: Optional[str] = None
        if field == "title":
            old_value = cur.get("title")
            payload["article"]["title"] = new_value
        elif field == "meta_description":
            old_value = cur.get("summary_html")
            payload["article"]["summary_html"] = new_value
        else:
            return ApplyResult(success=False, message=f"Unsupported field for articles: {field}")

        resp = await client.put(
            f"{self.api_base}/blogs/{blog_id}/articles/{art_id}.json",
            json=payload, headers=self._headers(),
        )
        if resp.status_code in (200, 201):
            return ApplyResult(
                success=True, message=f"Updated article {art_id}.{field}",
                rollback_value=old_value, applied_at=datetime.utcnow().isoformat(),
            )
        return ApplyResult(success=False, message=f"Shopify {resp.status_code}: {resp.text[:200]}")


def _parse_next_cursor(link_header: str | None) -> str | None:
    """Extract the page_info cursor from Shopify's Link header (rel=next)."""
    if not link_header:
        return None
    import re
    for part in link_header.split(","):
        if 'rel="next"' in part:
            m = re.search(r"page_info=([^&>]+)", part)
            if m:
                return m.group(1)
    return None
