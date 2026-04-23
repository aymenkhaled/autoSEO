"""Sitemap.xml parser — including gzipped and nested sitemaps."""
import httpx
import gzip
from xml.etree import ElementTree
from typing import AsyncGenerator
from urllib.parse import urljoin

from packages.crawler.url_utils import is_safe_url


async def discover_sitemap_urls(domain: str) -> AsyncGenerator[str, None]:
    sitemap_urls = [
        urljoin(domain, "/sitemap.xml"),
        urljoin(domain, "/sitemap_index.xml"),
        urljoin(domain, "/sitemap-index.xml"),
        urljoin(domain, "/sitemap.xml.gz"),
    ]
    seen: set = set()
    for sitemap_url in sitemap_urls:
        async for url in _parse_sitemap(sitemap_url, seen):
            yield url


async def _parse_sitemap(url: str, seen: set) -> AsyncGenerator[str, None]:
    if url in seen:
        return
    seen.add(url)
    if not is_safe_url(url):
        return
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
        except Exception:
            return
        if resp.status_code != 200 or not is_safe_url(str(resp.url)):
            return
        content = resp.content
        if url.endswith(".gz"):
            try:
                content = gzip.decompress(content)
            except Exception:
                return
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError:
            return
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        for sitemap in root.findall("sm:sitemap/sm:loc", ns):
            if sitemap.text and is_safe_url(sitemap.text.strip()):
                async for u in _parse_sitemap(sitemap.text.strip(), seen):
                    yield u
        for loc in root.findall("sm:url/sm:loc", ns):
            if loc.text and is_safe_url(loc.text.strip()):
                yield loc.text.strip()
