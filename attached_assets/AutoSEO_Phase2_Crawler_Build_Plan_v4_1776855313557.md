# AUTONOMOUS SEO AGENT — PHASE 2: SMART CRAWLER BUILD PLAN
### Version 4.0 — April 2026 | React + FastAPI | Deep Research-Backed
### Focused on: 4-Layer Crawler + SEO Signal Extraction + AI Analysis Pipeline

---

> **WHO THIS IS FOR:** AI Code Editor (Cursor / Claude Code / Windsurf)
> **WHERE YOU ARE:** Phase 1 (Foundation) is DONE. Infrastructure, auth, database, and global UI/UX are complete.
> **WHAT YOU'RE BUILDING NOW:** The entire crawling engine, SEO analysis pipeline, AI fix generation, and JS snippet.
> **TECH STACK:** React 19 + Vite (frontend), Python 3.12 + FastAPI (backend), Celery + Redis (workers), Supabase PostgreSQL

---

## TABLE OF CONTENTS

1. [Architecture Overview — The 5-Layer Data Collection Engine](#1-architecture-overview)
2. [What Changed From V3 — Critical Fixes Based on Research](#2-what-changed-from-v3)
3. [Layer 0: Pre-Crawl Intelligence (robots.txt + sitemap)](#3-layer-0)
4. [Layer 1: Jina AI Reader — Fast, No Browser](#4-layer-1)
5. [Layer 2: Crawl4AI + Camoufox — Anti-Detection Crawling](#5-layer-2)
6. [Layer 3: ScrapFly — Cloudflare/Bot Bypass Fallback](#6-layer-3)
7. [Layer 4: Client JS Snippet — Primary Field Data Source](#7-layer-4)
8. [Layer 5: CMS API Direct — 99% Reliable](#8-layer-5)
9. [Crawl Orchestrator — The Brain](#9-crawl-orchestrator)
10. [SEO Signal Extractor — Complete Implementation](#10-seo-signal-extractor)
11. [Issue Generator — Signals to Issues](#11-issue-generator)
12. [SEO Score Calculator](#12-seo-score-calculator)
13. [AI Fix Engine — Claude-Powered](#13-ai-fix-engine)
14. [Fix Verification + Rollback](#14-fix-verification)
15. [Crawl Progress + Real-Time Updates](#15-crawl-progress)
16. [Diamond Features — Revenue Multipliers](#16-diamond-features)
17. [Database Changes From V3](#17-database-changes)
18. [Complete File-by-File Implementation](#18-complete-implementation)
19. [Testing Strategy](#19-testing-strategy)
20. [Coding Checklist — Execute In Order](#20-coding-checklist)

---

## 1. ARCHITECTURE OVERVIEW

### The 5-Layer Data Collection Engine

```
                    ┌─────────────────────────────────┐
                    │     CRAWL REQUEST ARRIVES        │
                    │   (site_id, crawl_id, options)   │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │   LAYER 0: PRE-CRAWL INTEL       │
                    │   • robots.txt parser             │
                    │   • sitemap.xml parser             │
                    │   • Build URL priority queue       │
                    │   • Calculate crawl delay          │
                    └──────────────┬──────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                     │
    ┌─────────▼──────────┐ ┌──────▼───────┐ ┌──────────▼─────────┐
    │  LAYER 5: CMS API  │ │  LAYER 4:    │ │  CRAWLER LAYERS    │
    │  (if connected)    │ │  JS Snippet  │ │  (try in order)    │
    │  WordPress/Shopify │ │  (if active) │ │                    │
    │  Webflow/GitHub    │ │  Real users  │ │  L1: Jina Reader   │
    │  → 99% reliable    │ │  → 99% field │ │  L2: Crawl4AI      │
    │                    │ │              │ │  L3: ScrapFly       │
    └─────────┬──────────┘ └──────┬───────┘ └──────────┬─────────┘
              │                    │                     │
              └────────────────────┼────────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │    SEO SIGNAL EXTRACTOR           │
                    │    • Meta tags, headings, links   │
                    │    • Images, schema, social        │
                    │    • Performance, hreflang         │
                    │    • Technical SEO signals         │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │    CROSS-PAGE ANALYSIS            │
                    │    • Duplicate content (SimHash)  │
                    │    • Internal link graph          │
                    │    • Orphan page detection         │
                    │    • Canonical chain detection     │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │    ISSUE GENERATOR                │
                    │    • Map signals → issues          │
                    │    • Severity + impact scoring     │
                    │    • Calculate page/site scores    │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │    AI FIX ENGINE (Claude)          │
                    │    • Generate fixes per issue      │
                    │    • Confidence scoring             │
                    │    • Validation pipeline            │
                    │    • Content safety check           │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │    SAVE TO DATABASE                │
                    │    pages + issues + crawl stats    │
                    └─────────────────────────────────┘
```

### Layer Selection Logic (Per-URL)

```python
# Decision tree for each URL in the queue
async def select_layer(url: str, site: Site) -> CrawlResult:
    # Layer 5: CMS API (if connected) — skip all crawling
    if site.connection_type in ("wordpress", "shopify", "webflow"):
        result = await fetch_via_cms(site, url)
        if result:
            return result

    # Layer 4: JS Snippet data (if we have recent field data)
    snippet_data = await get_latest_snippet_data(site.id, url)
    if snippet_data and snippet_data.age_hours < 24:
        # Merge snippet field data with crawler lab data below
        pass

    # Layer 1: Jina AI Reader (fastest, free, no browser)
    result = await fetch_with_jina(url)
    if result and not is_blocked_content(result.html):
        return merge_with_snippet(result, snippet_data)

    # Layer 2: Crawl4AI + Camoufox (anti-detection browser)
    result = await fetch_with_crawl4ai(url)
    if result and not is_blocked_content(result.html):
        return merge_with_snippet(result, snippet_data)

    # Layer 3: ScrapFly (paid, highest success on Cloudflare)
    result = await fetch_with_scrapfly(url)
    if result and not is_blocked_content(result.html):
        return merge_with_snippet(result, snippet_data)

    # All layers failed
    return CrawlResult(url=url, status="failed", error="all_layers_exhausted")
```

---

## 2. WHAT CHANGED FROM V3 — CRITICAL FIXES

Based on deep research (April 2026), the following changes were made:

### Fix 1: Camoufox Integration Was Wrong

**V3 had:** `browser_type="firefox"` in Crawl4AI BrowserConfig, assuming Crawl4AI has native Camoufox support.

**Reality:** Crawl4AI does **NOT** have native Camoufox integration. Camoufox is a separate Playwright-compatible browser that must be launched independently and connected via CDP.

**V4 Fix:** Launch Camoufox separately, connect via CDP URL.

### Fix 2: Crawl4AI API Changed in v0.8.x

**V3 had:** Old API patterns that may not work with Crawl4AI 0.8.6.

**V4 Fix:** Updated to v0.8.6 API with:
- `init_scripts` for stealth JS injection
- `BFSDeepCrawlStrategy` with crash recovery
- `LXMLWebScrapingStrategy` for faster parsing
- Streaming deep crawl results
- Prefetch mode for link discovery

### Fix 3: ScrapFly Pricing Misunderstood

**V3 assumed:** ~$0.003 per request.

**Reality:** A single request with JS rendering + residential proxy costs **30+ credits**. On the $30/mo plan (200K credits), that's only ~6,667 hard requests/month.

**V4 Fix:** ScrapFly is ONLY used as last resort. Added cost tracking per crawl. Added budget alerts.

### Fix 4: Jina AI Reader API Updated

**V3 had:** Basic API without authentication.

**V4 Fix:** Added API key support for 100 RPM (vs 20 RPM free), added `X-With-Links-Summary` and `X-With-Images-Summary` headers for richer SEO data, added country-specific proxy option.

### Fix 5: JS Snippet Was Incomplete

**V3 had:** Basic snippet collecting only basic Web Vitals.

**V4 Fix:** Enhanced snippet with:
- INP (Interaction to Next Paint) — replaced FID as Core Web Vital in March 2024
- CLS collected properly via PerformanceObserver
- SPA navigation detection (MutationObserver + History API)
- Console error capture
- Broken resource detection
- Proper beacon batching (don't send on every page — batch every 30s)

### Fix 6: SEO Extractor Missing Fields

**V3 had:** Basic extraction.

**V4 Fix:** Added:
- Security header detection (HSTS, X-Robots-Tag, Content-Security-Policy)
- Mixed content detection
- Favicon detection
- Apple touch icon detection
- Web manifest detection
- Redirect chain extraction
- Canonical chain extraction
- hreflang bidirectional validation
- Image size detection (without downloading — use naturalWidth/Height from crawler)
- Duplicate meta tag detection (Yoast + Rank Math conflict)

### Fix 7: No CMS API Integration for Phase 2

**V3 put CMS in Phase 4** (weeks 7-10). But CMS API is the most reliable data source.

**V4 Fix:** Added a lightweight CMS API reader as Layer 5 in the crawler itself. Full write support still comes later, but reading data via CMS API is part of Phase 2.

---

## 3. LAYER 0: PRE-CRAWL INTELLIGENCE

### Why This Exists

Before crawling a single page, you need to know:
1. Which pages you're **allowed** to crawl (robots.txt)
2. Which pages the site owner **wants** indexed (sitemap.xml)
3. How fast you're allowed to crawl (Crawl-delay)
4. Which pages to prioritize (sitemap URLs first, then discovered)

### 3.1 robots.txt Parser

```python
# packages/crawler/pre_crawl/robots.py
import httpx
import structlog
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse

logger = structlog.get_logger()


class RobotsParser:
    """
    Fetches and parses robots.txt for a domain.
    Returns rules about what we can/cannot crawl.
    """

    def __init__(self, domain: str, user_agent: str = "AutoSEO-Bot"):
        self.domain = domain.rstrip("/")
        self.user_agent = user_agent
        self.parser = RobotFileParser()
        self.sitemaps: list[str] = []
        self.crawl_delay: float = 1.0
        self._fetched = False

    async def fetch(self) -> None:
        """Fetch and parse robots.txt from the domain."""
        robots_url = f"{self.domain}/robots.txt"
        async with httpx.AsyncClient(
            timeout=10,
            follow_redirects=True,
            headers={"User-Agent": self.user_agent},
        ) as client:
            try:
                resp = await client.get(robots_url)
                if resp.status_code == 200:
                    self.parser.parse(resp.text.splitlines())
                    self._fetched = True
                    # Extract sitemaps listed in robots.txt
                    for line in resp.text.splitlines():
                        line = line.strip().lower()
                        if line.startswith("sitemap:"):
                            sitemap_url = line.split(":", 1)[1].strip()
                            self.sitemaps.append(sitemap_url)
                    # Extract crawl delay
                    delay = self.parser.crawl_delay(self.user_agent)
                    self.crawl_delay = max(delay or 1.0, 1.0)
                    logger.info("robots_txt_parsed", domain=self.domain,
                                sitemaps_found=len(self.sitemaps),
                                crawl_delay=self.crawl_delay)
                else:
                    logger.info("robots_txt_not_found", domain=self.domain,
                                status=resp.status_code)
            except Exception as e:
                logger.warning("robots_txt_fetch_failed", domain=self.domain, error=str(e))

    def is_allowed(self, url: str) -> bool:
        """Check if a URL is allowed by robots.txt rules."""
        if not self._fetched:
            return True  # No robots.txt = all allowed
        return self.parser.can_fetch(self.user_agent, url)

    def get_disallowed_paths(self) -> list[str]:
        """Get all disallowed path patterns (for reporting to user)."""
        # RobotFileParser doesn't expose this directly, parse entries
        paths = []
        for entry in self.parser.entries:
            for rule in entry.rulelines:
                if not rule.allowance:
                    paths.append(rule.path)
        return paths

    def get_crawl_delay(self) -> float:
        """Return minimum delay between requests in seconds."""
        return self.crawl_delay
```

### 3.2 Sitemap Parser (Full Implementation)

```python
# packages/crawler/pre_crawl/sitemap.py
import httpx
import gzip
import structlog
from xml.etree import ElementTree
from typing import AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime

logger = structlog.get_logger()


@dataclass
class SitemapURL:
    """A single URL from a sitemap with optional metadata."""
    loc: str
    lastmod: datetime | None = None
    changefreq: str | None = None
    priority: float | None = None


@dataclass
class SitemapResult:
    """Complete sitemap parsing result."""
    urls: list[SitemapURL] = field(default_factory=list)
    sitemaps_found: list[str] = field(default_factory=list)
    total_urls: int = 0
    errors: list[str] = field(default_factory=list)


class SitemapParser:
    """
    Discovers and parses sitemap.xml files from a domain.
    Handles: sitemap.xml, sitemap_index.xml, gzipped sitemaps,
    nested sitemaps, and robots.txt-declared sitemaps.
    """

    NAMESPACE = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    def __init__(self, domain: str, extra_sitemaps: list[str] | None = None):
        self.domain = domain.rstrip("/")
        self.extra_sitemaps = extra_sitemaps or []
        self.seen_sitemaps: set[str] = set()
        self.urls: list[SitemapURL] = []
        self.errors: list[str] = []

    async def discover_all(self) -> SitemapResult:
        """Discover and parse all sitemaps for this domain."""
        # Standard sitemap locations
        candidates = [
            f"{self.domain}/sitemap.xml",
            f"{self.domain}/sitemap_index.xml",
            f"{self.domain}/sitemap-index.xml",
            f"{self.domain}/sitemap.xml.gz",
        ]
        # Add sitemaps from robots.txt
        candidates.extend(self.extra_sitemaps)

        for url in candidates:
            await self._parse_sitemap_recursive(url)

        return SitemapResult(
            urls=self.urls,
            sitemaps_found=list(self.seen_sitemaps),
            total_urls=len(self.urls),
            errors=self.errors,
        )

    async def _parse_sitemap_recursive(self, url: str, depth: int = 0) -> None:
        """Recursively parse sitemap index and URL set."""
        if url in self.seen_sitemaps or depth > 5:
            return
        self.seen_sitemaps.add(url)

        try:
            async with httpx.AsyncClient(
                timeout=30,
                follow_redirects=True,
                headers={"User-Agent": "AutoSEO-Bot"},
            ) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return

                content = resp.content
                if url.endswith(".gz"):
                    content = gzip.decompress(content)

                root = ElementTree.fromstring(content)

                # Check if this is a sitemap index
                sitemap_locs = root.findall("sm:sitemap/sm:loc", self.NAMESPACE)
                if not sitemap_locs:
                    # Also try without namespace (some sitemaps omit it)
                    sitemap_locs = root.findall(".sitemap/loc")

                for loc_elem in sitemap_locs:
                    if loc_elem.text:
                        await self._parse_sitemap_recursive(
                            loc_elem.text.strip(), depth + 1
                        )

                # Parse URL set
                for url_elem in root.findall("sm:url", self.NAMESPACE):
                    sitemap_url = self._parse_url_entry(url_elem)
                    if sitemap_url:
                        self.urls.append(sitemap_url)

                # Also try without namespace
                if not root.findall("sm:url", self.NAMESPACE):
                    for url_elem in root.findall("url"):
                        sitemap_url = self._parse_url_entry_no_ns(url_elem)
                        if sitemap_url:
                            self.urls.append(sitemap_url)

        except Exception as e:
            error_msg = f"Failed to parse sitemap {url}: {str(e)}"
            self.errors.append(error_msg)
            logger.warning("sitemap_parse_error", url=url, error=str(e))

    def _parse_url_entry(self, url_elem: ElementTree.Element) -> SitemapURL | None:
        loc = url_elem.find("sm:loc", self.NAMESPACE)
        if loc is None or not loc.text:
            return None

        lastmod_elem = url_elem.find("sm:lastmod", self.NAMESPACE)
        changefreq_elem = url_elem.find("sm:changefreq", self.NAMESPACE)
        priority_elem = url_elem.find("sm:priority", self.NAMESPACE)

        lastmod = None
        if lastmod_elem is not None and lastmod_elem.text:
            try:
                lastmod = datetime.fromisoformat(lastmod_elem.text.strip().replace("Z", "+00:00"))
            except ValueError:
                pass

        return SitemapURL(
            loc=loc.text.strip(),
            lastmod=lastmod,
            changefreq=changefreq_elem.text.strip() if changefreq_elem is not None else None,
            priority=float(priority_elem.text.strip()) if priority_elem is not None else None,
        )

    def _parse_url_entry_no_ns(self, url_elem: ElementTree.Element) -> SitemapURL | None:
        loc = url_elem.find("loc")
        if loc is None or not loc.text:
            return None
        return SitemapURL(loc=loc.text.strip())
```

### 3.3 URL Priority Queue

```python
# packages/crawler/pre_crawl/priority_queue.py
import heapq
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse


@dataclass(order=True)
class URLPriority:
    """Sortable URL with priority score. Lower score = higher priority."""
    sort_key: float = field(compare=True)
    url: str = field(compare=False)
    depth: int = field(compare=False)
    source: str = field(compare=False)  # "sitemap", "homepage", "discovered"


class CrawlPriorityQueue:
    """
    Prioritized URL queue for crawling.
    Sitemap URLs come first, then homepage-linked, then discovered.
    """

    def __init__(self):
        self._queue: list[URLPriority] = []
        self._seen: set[str] = set()
        self._domain: str | None = None

    @property
    def size(self) -> int:
        return len(self._queue)

    @property
    def seen_count(self) -> int:
        return len(self._seen)

    def add_sitemap_urls(self, urls: list[str], max_pages: int = 500) -> None:
        """Add sitemap URLs with highest priority (score 0-0.3)."""
        for i, url in enumerate(urls[:max_pages]):
            if url not in self._seen:
                priority = min(i / max_pages * 0.3, 0.3)
                heapq.heappush(self._queue, URLPriority(
                    sort_key=priority, url=url, depth=0, source="sitemap"
                ))
                self._seen.add(url)

    def add_homepage_links(self, urls: list[str]) -> None:
        """Add homepage-discovered links with medium priority (score 0.3-0.6)."""
        for i, url in enumerate(urls):
            if url not in self._seen:
                priority = 0.3 + min(i / max(len(urls), 1) * 0.3, 0.3)
                heapq.heappush(self._queue, URLPriority(
                    sort_key=priority, url=url, depth=1, source="homepage"
                ))
                self._seen.add(url)

    def add_discovered_urls(self, urls: list[str], depth: int = 2) -> None:
        """Add discovered links with lower priority (score 0.6-1.0)."""
        for i, url in enumerate(urls):
            if url not in self._seen:
                priority = 0.6 + min(i / max(len(urls), 1) * 0.4, 0.4)
                heapq.heappush(self._queue, URLPriority(
                    sort_key=priority, url=url, depth=depth, source="discovered"
                ))
                self._seen.add(url)

    def pop(self) -> URLPriority | None:
        """Get the next highest-priority URL."""
        if self._queue:
            return heapq.heappop(self._queue)
        return None

    def is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain as the first URL added."""
        parsed = urlparse(url)
        if self._domain is None:
            self._domain = parsed.netloc
        return parsed.netloc == self._domain or parsed.netloc == ""
```

---

## 4. LAYER 1: JINA AI READER

### When to Use
- Static HTML sites, blogs, simple WordPress sites
- Any URL as first attempt (it's free and fast)
- NOT for: Cloudflare-protected sites, JS-heavy SPAs

### Updated API (April 2026)

```python
# packages/crawler/layers/jina_layer.py
import httpx
import structlog
from dataclasses import dataclass
from typing import Optional

logger = structlog.get_logger()


@dataclass
class JinaResult:
    """Result from Jina AI Reader."""
    url: str
    title: str
    content_markdown: str
    content_html: str | None = None
    links: list[dict] | None = None
    images: list[dict] | None = None
    source: str = "jina"


class JinaLayer:
    """
    Layer 1: Jina AI Reader (r.jina.ai)
    Fast, no browser, server-side JS rendering.
    Free: 20 RPM without key, 100 RPM with key.
    Returns LLM-ready Markdown + metadata.
    """

    BASE_URL = "https://r.jina.ai/"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self.headers = {
            "Accept": "application/json",
            "X-Return-Format": "markdown",
            "X-With-Links-Summary": "true",   # Get all links from page
            "X-With-Images-Summary": "true",  # Get all images from page
        }
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    async def fetch(self, url: str, country: str | None = None) -> JinaResult | None:
        """
        Fetch a URL via Jina AI Reader.
        Returns None if blocked or failed (caller should try next layer).
        """
        jina_url = f"{self.BASE_URL}{url}"
        headers = {**self.headers}
        if country:
            headers["X-Country-Code"] = country

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(jina_url, headers=headers)

                if resp.status_code == 200:
                    data = resp.json()
                    page_data = data.get("data", {})

                    return JinaResult(
                        url=url,
                        title=page_data.get("title", ""),
                        content_markdown=page_data.get("content", ""),
                        content_html=page_data.get("html", None),
                        links=page_data.get("links", None),
                        images=page_data.get("images", None),
                        source="jina",
                    )

                # Detect anti-bot blocks — fall through to Layer 2
                if resp.status_code in (403, 429, 503):
                    logger.info("jina_blocked", url=url, status=resp.status_code)
                    return None

                logger.info("jina_failed", url=url, status=resp.status_code)
                return None

            except httpx.TimeoutException:
                logger.warning("jina_timeout", url=url)
                return None
            except Exception as e:
                logger.error("jina_error", url=url, error=str(e))
                return None
```

### What Jina Returns vs What We Need

Jina returns **Markdown content** — great for AI analysis but missing SEO signals. We need HTML for the SEO extractor.

**Solution:** Use `X-Return-Format: html` for the first request to get raw HTML for SEO extraction, then use Markdown for AI content analysis.

```python
async def fetch_for_seo(self, url: str) -> dict | None:
    """Fetch with HTML format for SEO signal extraction."""
    jina_url = f"{self.BASE_URL}{url}"
    headers = {**self.headers, "X-Return-Format": "html"}

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(jina_url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "url": url,
                    "html": data.get("data", {}).get("content", ""),
                    "title": data.get("data", {}).get("title", ""),
                    "source": "jina",
                }
            return None
        except Exception:
            return None
```

---

## 5. LAYER 2: CRAWL4AI + CAMOUFOX

### The Anti-Detection Problem (2026 Reality)

Standard Playwright/Puppeteer is **detected immediately** by:
1. `navigator.webdriver` = true
2. Chrome DevTools Protocol fingerprint
3. Missing browser plugins (PDF viewer, etc.)
4. Unusual viewport sizes
5. Canvas/WebGL fingerprint anomalies

### Camoufox: How It Actually Works

Camoufox is a **custom Firefox build** that injects fingerprints at the **C++ engine level** — not via JavaScript injection (which is detectable). It uses **BrowserForge** to rotate device characteristics that statistically match real-world browser distributions ("crowdblending" rather than "hardening").

**Key limitation discovered:** Crawl4AI does **NOT** have native Camoufox support. You must:
1. Launch Camoufox separately
2. Get its CDP debugging URL
3. Connect Crawl4AI to that URL

### Implementation

```python
# packages/crawler/layers/crawl4ai_layer.py
import asyncio
import structlog
from dataclasses import dataclass
from typing import AsyncGenerator

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain, SEOFilter
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy

logger = structlog.get_logger()


@dataclass
class Crawl4AIResult:
    """Result from Crawl4AI crawling."""
    url: str
    html: str
    markdown: str
    status_code: int
    depth: int
    links: list[str]
    source: str = "crawl4ai"


class Crawl4AILayer:
    """
    Layer 2: Crawl4AI with anti-detection browser.
    Can be used with:
      - Built-in Chromium (no anti-detection)
      - Camoufox via CDP (anti-detection)
      - SeleniumBase UC Mode via CDP (alternative)
    """

    def __init__(
        self,
        use_camoufox: bool = True,
        max_pages: int = 500,
        max_depth: int = 5,
        crawl_delay: float = 1.5,
        camoufox_debug_port: int = 9222,
    ):
        self.use_camoufox = use_camoufox
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.crawl_delay = crawl_delay
        self.camoufox_debug_port = camoufox_debug_port
        self._camoufox_process = None

    async def _start_camoufox(self) -> str | None:
        """
        Launch Camoufox with debugging port and return CDP URL.
        Camoufox must be installed: pip install camoufox && python -m camoufox fetch
        """
        try:
            from camoufox.async_api import AsyncCamoufox

            camoufox = AsyncCamoufox(
                os=["windows", "macos"],  # Random OS fingerprint
                debugging_port=self.camoufox_debug_port,
                humanize=True,  # Human-like mouse movements
            )
            browser = await camoufox.__aenter__()
            self._camoufox_browser = camoufox
            cdp_url = f"http://localhost:{self.camoufox_debug_port}"
            logger.info("camoufox_started", cdp_url=cdp_url)
            return cdp_url
        except ImportError:
            logger.warning("camoufox_not_installed", msg="pip install camoufox && python -m camoufox fetch")
            return None
        except Exception as e:
            logger.error("camoufox_start_failed", error=str(e))
            return None

    async def _stop_camoufox(self) -> None:
        """Clean up Camoufox browser."""
        if hasattr(self, '_camoufox_browser'):
            try:
                await self._camoufox_browser.__aexit__(None, None, None)
            except Exception:
                pass

    def _get_browser_config(self, cdp_url: str | None = None) -> BrowserConfig:
        """Create BrowserConfig with or without Camoufox."""
        if cdp_url:
            # Connect to Camoufox via CDP
            return BrowserConfig(
                browser_mode="custom",
                cdp_url=cdp_url,
            )
        else:
            # Fallback: built-in Chromium with stealth
            return BrowserConfig(
                browser_type="chromium",
                headless=True,
                enable_stealth=True,
                init_scripts=[
                    # Override navigator.webdriver
                    "Object.defineProperty(navigator, 'webdriver', {get: () => false})",
                    # Override plugins length
                    "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})",
                    # Override languages
                    "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})",
                ],
            )

    async def crawl_single(self, url: str) -> Crawl4AIResult | None:
        """
        Crawl a single URL with Crawl4AI.
        Does NOT follow links — just fetches one page.
        Use for Layer 2 fallback on individual URLs.
        """
        cdp_url = None
        if self.use_camoufox:
            cdp_url = await self._start_camoufox()

        try:
            browser_config = self._get_browser_config(cdp_url)
            crawl_config = CrawlerRunConfig(
                scraping_strategy=LXMLWebScrapingStrategy(),  # Faster than BeautifulSoup
                wait_for="networkidle",
                page_timeout=30000,
                mean_delay=self.crawl_delay,
                max_range=0.5,
                # Exclude non-content elements
                exclude_external_links=False,  # We need all links for SEO
                word_count_threshold=5,
                # Get structured data
                css_selector="html",  # Get full HTML for SEO extraction
            )

            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=crawl_config)

                if result.success:
                    return Crawl4AIResult(
                        url=result.url,
                        html=result.html,
                        markdown=result.markdown.raw_markdown if result.markdown else "",
                        status_code=result.status_code or 200,
                        depth=0,
                        links=result.links.get("external", []) + result.links.get("internal", []),
                        source="crawl4ai",
                    )

                logger.warning("crawl4ai_page_failed", url=url, error=result.error_message)
                return None

        except Exception as e:
            logger.error("crawl4ai_error", url=url, error=str(e))
            return None
        finally:
            await self._stop_camoufox()

    async def crawl_site(
        self, start_url: str, callback=None
    ) -> AsyncGenerator[Crawl4AIResult, None]:
        """
        Deep crawl an entire site with BFS strategy.
        Yields results as they arrive (streaming mode).
        """
        cdp_url = None
        if self.use_camoufox:
            cdp_url = await self._start_camoufox()

        try:
            browser_config = self._get_browser_config(cdp_url)
            crawl_config = CrawlerRunConfig(
                deep_crawl_strategy=BFSDeepCrawlStrategy(
                    max_depth=self.max_depth,
                    max_pages=self.max_pages,
                    include_external=False,
                    filter_chain=FilterChain([
                        SEOFilter(threshold=0.3)
                    ]),
                ),
                scraping_strategy=LXMLWebScrapingStrategy(),
                wait_for="networkidle",
                page_timeout=30000,
                mean_delay=self.crawl_delay,
                max_range=0.5,
                word_count_threshold=5,
                streaming=True,  # Stream results as they arrive
            )

            async with AsyncWebCrawler(config=browser_config) as crawler:
                async for result in await crawler.arun(url=start_url, config=crawl_config):
                    if result.success:
                        page_result = Crawl4AIResult(
                            url=result.url,
                            html=result.html,
                            markdown=result.markdown.raw_markdown if result.markdown else "",
                            status_code=result.status_code or 200,
                            depth=result.metadata.get("depth", 0) if result.metadata else 0,
                            links=result.links.get("external", []) + result.links.get("internal", []),
                            source="crawl4ai",
                        )
                        if callback:
                            await callback(page_result)
                        yield page_result

        except Exception as e:
            logger.error("crawl4ai_site_error", url=start_url, error=str(e))
        finally:
            await self._stop_camoufox()
```

### Anti-Detection Checklist for Crawl4AI

```python
# packages/crawler/layers/anti_detect.py
"""Utilities for detecting and handling anti-bot blocks."""

BLOCKED_SIGNALS = [
    "just a moment",
    "checking your browser",
    "cf-browser-verification",
    "ddos protection by cloudflare",
    "datadome",
    "please complete the security check",
    "are you a robot",
    "attention required",
    "ray id",  # Cloudflare error page
    "challenge-platform",
    "captcha",
    "perimeterx",
    "px-captcha",
    "akamai",
]


def is_blocked_content(html: str) -> bool:
    """Check if HTML content is a bot detection challenge page."""
    if not html:
        return True  # Empty = blocked
    html_lower = html.lower()
    return any(signal in html_lower for signal in BLOCKED_SIGNALS)


def is_cloudflare_challenge(status_code: int, html: str) -> bool:
    """Specifically detect Cloudflare challenge pages."""
    if status_code in (403, 503):
        return is_blocked_content(html)
    if status_code == 200 and is_blocked_content(html):
        return True  # Some CF challenges return 200 with JS challenge
    return False


def should_fallback_to_scrapfly(status_code: int, html: str) -> bool:
    """Decide if we should fall through to ScrapFly layer."""
    return is_cloudflare_challenge(status_code, html) or status_code in (403, 429, 503)
```

---

## 6. LAYER 3: SCRAPFLY

### When to Use
- Cloudflare Turnstile / DataDome / PerimeterX / Akamai protected sites
- Only after Layers 1 and 2 both fail
- Cost: **30+ credits per request** with JS rendering + residential proxy

### Budget Management

```python
# packages/crawler/layers/scrapfly_layer.py
import httpx
import structlog
from dataclasses import dataclass
from typing import Optional

logger = structlog.get_logger()


@dataclass
class ScrapFlyUsage:
    """Track ScrapFly credit usage per crawl."""
    credits_used: int = 0
    requests_made: int = 0
    budget_limit: int = 5000  # Default per crawl


class ScrapFlyLayer:
    """
    Layer 3: ScrapFly API (paid, highest success rate)
    Handles Cloudflare Turnstile, DataDome, PerimeterX, Akamai.
    Cost: 1 base credit + 5 (JS) + 25 (residential) = 31 credits per "hard" request.
    On $30/mo plan (200K credits): ~6,451 hard requests/month.
    """

    BASE_URL = "https://api.scrapfly.io/scrape"

    def __init__(
        self,
        api_key: str,
        budget_per_crawl: int = 5000,
        use_residential_proxy: bool = True,
    ):
        self.api_key = api_key
        self.budget = ScrapFlyUsage(budget_limit=budget_per_crawl)
        self.use_residential_proxy = use_residential_proxy

    def _calculate_credits(self, render_js: bool, residential: bool) -> int:
        """Calculate credit cost for a request."""
        credits = 1  # Base
        if render_js:
            credits += 5
        if residential:
            credits += 25
        return credits

    async def fetch(self, url: str, country: str = "US") -> dict | None:
        """
        Fetch a URL via ScrapFly with ASP bypass.
        Returns None if budget exhausted or request failed.
        """
        render_js = True
        residential = self.use_residential_proxy
        cost = self._calculate_credits(render_js, residential)

        # Budget check
        if self.budget.credits_used + cost > self.budget.budget_limit:
            logger.warning("scrapfly_budget_exhausted",
                           used=self.budget.credits_used,
                           limit=self.budget.budget_limit)
            return None

        params = {
            "key": self.api_key,
            "url": url,
            "asp": "true",           # Anti-Scraping Protection bypass
            "render_js": "true" if render_js else "false",
            "rendering_wait": "2000",
            "country": country,
            "retry": "false",        # We handle retries at orchestrator level
        }
        if residential:
            params["proxy_pool"] = "public_residential"

        async with httpx.AsyncClient(timeout=60) as client:
            try:
                resp = await client.get(self.BASE_URL, params=params)
                self.budget.credits_used += cost
                self.budget.requests_made += 1

                if resp.status_code == 200:
                    data = resp.json()
                    result = data.get("result", {})
                    return {
                        "url": url,
                        "html": result.get("content", ""),
                        "status_code": result.get("status_code", 200),
                        "source": "scrapfly",
                        "credits_cost": cost,
                    }

                logger.warning("scrapfly_failed", url=url,
                               status=resp.status_code,
                               credits_cost=cost)
                return None

            except Exception as e:
                logger.error("scrapfly_error", url=url, error=str(e))
                return None

    def get_usage_report(self) -> dict:
        """Return credit usage report for this crawl."""
        return {
            "credits_used": self.budget.credits_used,
            "requests_made": self.budget.requests_made,
            "budget_limit": self.budget.budget_limit,
            "budget_remaining": self.budget.budget_limit - self.budget.credits_used,
        }
```

---

## 7. LAYER 4: CLIENT JS SNIPPET

### Why This Is Your Most Important Data Source

The JS snippet is the **only data source that matches what Google actually measures**. It runs in real visitors' browsers, captures real Core Web Vitals, and sees the fully-rendered page (including JS-injected meta tags).

**No competitor can crawl your client's site better than a script running on the site itself.** This is your moat.

### Enhanced Snippet (v4)

```javascript
// packages/snippet/autoseo-snippet.js
// Embed: <script src="https://cdn.autoseo.com/snippet.js" data-token="SITE_TOKEN" async></script>
// Size: ~5KB minified
(function() {
  'use strict';

  var TOKEN = document.currentScript.getAttribute('data-token');
  var ENDPOINT = 'https://api.autoseo.com/snippet/collect';
  var BATCH_INTERVAL = 30000; // 30 seconds batch
  var MAX_BATCH_SIZE = 10;

  if (!TOKEN) return; // No token = do nothing

  var batch = [];
  var batchTimer = null;

  function addToBatch(data) {
    batch.push(data);
    if (batch.length >= MAX_BATCH_SIZE) {
      flushBatch();
    } else if (!batchTimer) {
      batchTimer = setTimeout(flushBatch, BATCH_INTERVAL);
    }
  }

  function flushBatch() {
    if (batch.length === 0) return;
    var payload = JSON.stringify({ token: TOKEN, events: batch });
    navigator.sendBeacon(ENDPOINT, payload);
    batch = [];
    if (batchTimer) { clearTimeout(batchTimer); batchTimer = null; }
  }

  function collectPageData() {
    var data = {
      url: window.location.href,
      timestamp: Date.now(),
      // SEO signals (after JS rendering)
      title: document.title || null,
      meta_description: getMeta('name', 'description'),
      canonical: getLink('rel', 'canonical'),
      h1: getText('h1'),
      robots: getMeta('name', 'robots'),
      viewport: getMeta('name', 'viewport'),
      // Social
      og_title: getMeta('property', 'og:title'),
      og_description: getMeta('property', 'og:description'),
      og_image: getMeta('property', 'og:image'),
      og_type: getMeta('property', 'og:type'),
      twitter_card: getMeta('name', 'twitter:card'),
      twitter_image: getMeta('name', 'twitter:image'),
      // Schema
      schema: getSchemaData(),
      // Performance (placeholder — filled by observers)
      lcp: null,
      inp: null,   // REPLACED FID — new Core Web Vital since March 2024
      cls: null,
      ttfb: null,
      // Browser context
      user_agent: navigator.userAgent,
      viewport_width: window.innerWidth,
      viewport_height: window.innerHeight,
      connection_type: navigator.connection ? navigator.connection.effectiveType : null,
      // Errors
      js_errors: [],
      broken_resources: [],
    };

    // Collect JS errors from this page
    if (window.__autoseo_errors) {
      data.js_errors = window.__autoseo_errors.slice(0, 5); // Max 5 errors
    }

    // Collect broken resources
    if (window.__autoseo_broken) {
      data.broken_resources = window.__autoseo_broken.slice(0, 10); // Max 10
    }

    // Core Web Vitals observers
    observeWebVitals(data);

    // Add to batch
    addToBatch(data);
  }

  // Helper functions
  function getMeta(attr, value) {
    var el = document.querySelector('meta[' + attr + '="' + value + '"]');
    return el ? el.content || null : null;
  }

  function getLink(attr, value) {
    var el = document.querySelector('link[' + attr + '="' + value + '"]');
    return el ? el.href || null : null;
  }

  function getText(selector) {
    var el = document.querySelector(selector);
    return el ? el.innerText.trim() : null;
  }

  function getSchemaData() {
    var scripts = document.querySelectorAll('script[type="application/ld+json"]');
    var schemas = [];
    scripts.forEach(function(s) {
      try { schemas.push(JSON.parse(s.textContent)); }
      catch(e) { /* invalid JSON-LD, still track it */ schemas.push({ _error: s.textContent.substring(0, 200) }); }
    });
    return schemas.length > 0 ? JSON.stringify(schemas) : null;
  }

  function observeWebVitals(data) {
    if (!('PerformanceObserver' in window)) return;

    // LCP (Largest Contentful Paint)
    try {
      new PerformanceObserver(function(list) {
        var entries = list.getEntries();
        if (entries.length > 0) {
          data.lcp = Math.round(entries[entries.length - 1].startTime);
          flushBatch(); // Send immediately when LCP is captured
        }
      }).observe({ type: 'largest-contentful-paint', buffered: true });
    } catch(e) {}

    // INP (Interaction to Next Paint) — replaces FID
    try {
      var maxINP = 0;
      new PerformanceObserver(function(list) {
        list.getEntries().forEach(function(entry) {
          if (entry.interactionId) {
            var inp = entry.duration;
            if (inp > maxINP) {
              maxINP = inp;
              data.inp = Math.round(maxINP);
            }
          }
        });
      }).observe({ type: 'event', buffered: true });
    } catch(e) {}

    // CLS (Cumulative Layout Shift)
    try {
      var clsValue = 0;
      var clsEntries = [];
      var sessionValue = 0;
      var sessionEntries = [];

      new PerformanceObserver(function(list) {
        list.getEntries().forEach(function(entry) {
          if (!entry.hadRecentInput) {
            var firstSessionEntry = sessionEntries[0];
            var lastSessionEntry = sessionEntries[sessionEntries.length - 1];

            if (sessionValue && entry.startTime - lastSessionEntry.startTime < 1000 &&
                entry.startTime - firstSessionEntry.startTime < 5000) {
              sessionValue += entry.value;
              sessionEntries.push(entry);
            } else {
              sessionValue = entry.value;
              sessionEntries = [entry];
            }

            if (sessionValue > clsValue) {
              clsValue = sessionValue;
              clsEntries = sessionEntries.slice();
              data.cls = Math.round(clsValue * 1000) / 1000;
            }
          }
        });
      }).observe({ type: 'layout-shift', buffered: true });
    } catch(e) {}

    // TTFB (Time to First Byte)
    try {
      var navEntry = performance.getEntriesByType('navigation')[0];
      if (navEntry) {
        data.ttfb = Math.round(navEntry.responseStart - navEntry.requestStart);
      }
    } catch(e) {}
  }

  // Error tracking
  window.__autoseo_errors = [];
  window.addEventListener('error', function(e) {
    if (window.__autoseo_errors.length < 5) {
      window.__autoseo_errors.push({
        message: e.message ? e.message.substring(0, 200) : '',
        filename: e.filename || '',
        lineno: e.lineno || 0,
      });
    }
  });

  // Broken resource tracking
  window.__autoseo_broken = [];
  window.addEventListener('error', function(e) {
    if (e.target && e.target.tagName) {
      if (window.__autoseo_broken.length < 10) {
        window.__autoseo_broken.push({
          tag: e.target.tagName.toLowerCase(),
          src: e.target.src || e.target.href || '',
        });
      }
    }
  }, true);

  // Collect on page load
  if (document.readyState === 'complete') {
    collectPageData();
  } else {
    window.addEventListener('load', collectPageData);
  }

  // SPA navigation detection
  var lastUrl = location.href;
  var urlObserver = new MutationObserver(function() {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      // Wait for SPA to render new content
      setTimeout(collectPageData, 1500);
    }
  });
  urlObserver.observe(document.body || document.documentElement, {
    childList: true, subtree: true
  });

  // Also catch History API changes
  var origPushState = history.pushState;
  var origReplaceState = history.replaceState;
  history.pushState = function() {
    origPushState.apply(this, arguments);
    setTimeout(collectPageData, 1500);
  };
  history.replaceState = function() {
    origReplaceState.apply(this, arguments);
    setTimeout(collectPageData, 1500);
  };
  window.addEventListener('popstate', function() {
    setTimeout(collectPageData, 1500);
  });

  // Flush on page unload
  window.addEventListener('beforeunload', flushBatch);
  window.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'hidden') flushBatch();
  });
})();
```

### Snippet Data Collection Endpoint

```python
# apps/api/routers/snippet.py
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()
router = APIRouter(tags=["snippet"])


class SnippetEvent(BaseModel):
    url: str
    timestamp: int
    title: str | None = None
    meta_description: str | None = None
    canonical: str | None = None
    h1: str | None = None
    robots: str | None = None
    og_title: str | None = None
    og_description: str | None = None
    og_image: str | None = None
    og_type: str | None = None
    twitter_card: str | None = None
    twitter_image: str | None = None
    schema: str | None = None
    lcp: int | None = None
    inp: int | None = None
    cls: float | None = None
    ttfb: int | None = None
    user_agent: str | None = None
    viewport_width: int | None = None
    viewport_height: int | None = None
    connection_type: str | None = None
    js_errors: list[dict] | None = None
    broken_resources: list[dict] | None = None


class SnippetPayload(BaseModel):
    token: str
    events: list[SnippetEvent]


@router.post("/snippet/collect")
async def collect_snippet_data(request: Request, payload: SnippetPayload):
    """
    Receive data from client-side JS snippet.
    This endpoint is PUBLIC (no auth required — token identifies the site).
    Rate limited to prevent abuse.
    """
    # Look up site by snippet token
    site = await db.get_site_by_snippet_token(payload.token)
    if not site:
        raise HTTPException(status_code=404, detail="Invalid snippet token")

    events_stored = 0
    for event in payload.events:
        try:
            await db.insert_snippet_event(
                site_id=site.id,
                org_id=site.org_id,
                page_url=event.url,
                title=event.title,
                meta_description=event.meta_description,
                canonical_url=event.canonical,
                h1_text=event.h1,
                schema_json=event.schema,
                lcp_ms=event.lcp,
                cls_score=event.cls,
                ttfb_ms=event.ttfb,
                user_agent=event.user_agent,
                viewport_width=event.viewport_width,
            )
            events_stored += 1
        except Exception as e:
            logger.error("snippet_event_store_failed", site_id=str(site.id), error=str(e))

    logger.info("snippet_data_collected", site_id=str(site.id),
                events=events_stored, total=len(payload.events))
    return {"status": "ok", "events_stored": events_stored}
```

---

## 8. LAYER 5: CMS API DIRECT

### Read-Only CMS Integration (Phase 2)

Full write support comes later. For Phase 2, we only **read** data via CMS APIs. This gives us the most reliable data source when available.

```python
# packages/crawler/layers/cms_layer.py
import httpx
import structlog
from typing import Optional

logger = structlog.get_logger()


class CMSReader:
    """
    Layer 5: Read site data directly from CMS APIs.
    99% reliable, structured data, no anti-bot issues.
    """

    async def read_wordpress(self, site) -> list[dict]:
        """Read pages and posts from WordPress REST API."""
        # Decrypt CMS token
        token = decrypt_credential(site.org_id, site.cms_token_encrypted, site.cms_token_iv)
        base_url = site.cms_endpoint or f"{site.domain}/wp-json/wp/v2"

        pages = []
        async with httpx.AsyncClient(
            timeout=30,
            headers={"Authorization": f"Basic {token}"},
        ) as client:
            # Fetch pages
            page = 1
            while True:
                resp = await client.get(
                    f"{base_url}/pages",
                    params={"per_page": 100, "page": page, "status": "publish"},
                )
                if resp.status_code != 200:
                    break
                data = resp.json()
                if not data:
                    break

                for wp_page in data:
                    pages.append({
                        "url": wp_page.get("link", ""),
                        "title": wp_page.get("title", {}).get("rendered", ""),
                        "content": wp_page.get("content", {}).get("rendered", ""),
                        "source": "wordpress_api",
                        "cms_id": wp_page.get("id"),
                        "modified": wp_page.get("modified"),
                        "yoast_meta": wp_page.get("yoast_head_json"),  # If Yoast REST API enabled
                    })

                if len(data) < 100:
                    break
                page += 1

            # Fetch posts
            page = 1
            while True:
                resp = await client.get(
                    f"{base_url}/posts",
                    params={"per_page": 100, "page": page, "status": "publish"},
                )
                if resp.status_code != 200:
                    break
                data = resp.json()
                if not data:
                    break

                for wp_post in data:
                    pages.append({
                        "url": wp_post.get("link", ""),
                        "title": wp_post.get("title", {}).get("rendered", ""),
                        "content": wp_post.get("content", {}).get("rendered", ""),
                        "source": "wordpress_api",
                        "cms_id": wp_post.get("id"),
                        "modified": wp_post.get("modified"),
                        "yoast_meta": wp_post.get("yoast_head_json"),
                    })

                if len(data) < 100:
                    break
                page += 1

        logger.info("wordpress_read_complete", site_id=str(site.id), pages=len(pages))
        return pages

    async def read_shopify(self, site) -> list[dict]:
        """Read products and pages from Shopify GraphQL API."""
        token = decrypt_credential(site.org_id, site.cms_token_encrypted, site.cms_token_iv)
        shop_domain = site.cms_endpoint  # e.g., "mystore.myshopify.com"

        pages = []
        cursor = None
        async with httpx.AsyncClient(
            timeout=30,
            headers={"X-Shopify-Access-Token": token},
        ) as client:
            # Fetch products
            while True:
                query = """
                query ($cursor: String) {
                  products(first: 100, after: $cursor) {
                    pageInfo { hasNextPage, endCursor }
                    edges {
                      node {
                        id, title, handle, description, onlineStoreUrl,
                        seo { title, description }
                        featuredImage { altText }
                      }
                    }
                  }
                }
                """
                resp = await client.post(
                    f"https://{shop_domain}/admin/api/2025-04/graphql.json",
                    json={"query": query, "variables": {"cursor": cursor}},
                )
                if resp.status_code != 200:
                    break

                data = resp.json()
                products = data.get("data", {}).get("products", {})
                for edge in products.get("edges", []):
                    node = edge["node"]
                    pages.append({
                        "url": node.get("onlineStoreUrl", ""),
                        "title": node.get("seo", {}).get("title") or node.get("title", ""),
                        "meta_description": node.get("seo", {}).get("description", ""),
                        "content": node.get("description", ""),
                        "source": "shopify_api",
                        "cms_id": node.get("id"),
                    })

                if not products.get("pageInfo", {}).get("hasNextPage"):
                    break
                cursor = products["pageInfo"]["endCursor"]

        logger.info("shopify_read_complete", site_id=str(site.id), pages=len(pages))
        return pages
```

---

## 9. CRAWL ORCHESTRATOR — THE BRAIN

### Complete Crawl Flow

```python
# workers/tasks/crawl.py
import asyncio
import time
from datetime import datetime, timezone

from celery import shared_task
import structlog

from packages.crawler.pre_crawl.robots import RobotsParser
from packages.crawler.pre_crawl.sitemap import SitemapParser
from packages.crawler.pre_crawl.priority_queue import CrawlPriorityQueue
from packages.crawler.layers.jina_layer import JinaLayer
from packages.crawler.layers.crawl4ai_layer import Crawl4AILayer
from packages.crawler.layers.scrapfly_layer import ScrapFlyLayer
from packages.crawler.layers.anti_detect import is_blocked_content, should_fallback_to_scrapfly
from packages.crawler.extractor import SEOExtractor
from packages.crawler.analyzer import (
    detect_duplicates, analyze_link_graph, detect_canonical_chains,
    detect_redirect_chains, validate_hreflang,
)
from packages.crawler.issue_generator import IssueGenerator
from packages.crawler.score_calculator import calculate_page_score, calculate_site_score

logger = structlog.get_logger()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_site_crawl(self, site_id: str, crawl_id: str):
    """Celery task: Run a full site crawl."""
    asyncio.run(_async_crawl(site_id, crawl_id))


async def _async_crawl(site_id: str, crawl_id: str):
    """Main crawl orchestration — runs the entire crawl pipeline."""

    start_time = time.time()
    site = await db.get_site(site_id)

    await db.update_crawl(crawl_id, status="running", started_at=datetime.now(timezone.utc))

    # Publish crawl progress events
    await publish_crawl_progress(crawl_id, "starting", "Initializing crawl...")

    try:
        # ── STEP 1: Pre-crawl intelligence ──────────────────────
        await publish_crawl_progress(crawl_id, "pre_crawl", "Checking robots.txt and sitemap...")

        # 1a: robots.txt
        robots = RobotsParser(site.domain)
        await robots.fetch()

        # 1b: sitemap.xml
        sitemap_parser = SitemapParser(site.domain, extra_sitemaps=robots.sitemaps)
        sitemap_result = await sitemap_parser.discover_all()

        # 1c: Build priority queue
        queue = CrawlPriorityQueue()
        sitemap_urls = [u.loc for u in sitemap_result.urls]
        queue.add_sitemap_urls(sitemap_urls, max_pages=site.crawl_max_pages)

        await db.update_crawl(crawl_id, pages_total=queue.size)
        logger.info("pre_crawl_complete", site_id=site_id,
                     sitemap_urls=len(sitemap_urls),
                     disallowed_paths=len(robots.get_disallowed_paths()))

        # ── STEP 2: Select crawl strategy ───────────────────────
        pages_data = []

        if site.connection_type in ("wordpress", "shopify", "webflow"):
            # Layer 5: CMS API (most reliable)
            await publish_crawl_progress(crawl_id, "cms_read", "Reading from CMS API...")
            cms_reader = CMSReader()
            if site.connection_type == "wordpress":
                pages_data = await cms_reader.read_wordpress(site)
            elif site.connection_type == "shopify":
                pages_data = await cms_reader.read_shopify(site)
        else:
            # Layer 1-3: Web crawling with fallback chain
            pages_data = await _tiered_crawl(
                site=site,
                queue=queue,
                robots=robots,
                crawl_id=crawl_id,
            )

        # ── STEP 3: Extract SEO signals ─────────────────────────
        await publish_crawl_progress(crawl_id, "extracting", "Extracting SEO signals...")

        extracted = []
        for i, page_data in enumerate(pages_data):
            if page_data.get("html"):
                signals = SEOExtractor(page_data["html"], page_data["url"]).extract_all()
            else:
                # CMS API data — no HTML to parse, use direct fields
                signals = _extract_from_cms_data(page_data)

            signals["url"] = page_data["url"]
            signals["crawl_source"] = page_data.get("source", "unknown")

            # Merge snippet field data if available
            snippet_data = await get_latest_snippet_data(site.id, page_data["url"])
            if snippet_data:
                signals = _merge_lab_and_field(signals, snippet_data)

            extracted.append(signals)

            # Progress update every 10 pages
            if i % 10 == 0:
                await publish_crawl_progress(crawl_id, "extracting",
                    f"Extracted {i+1}/{len(pages_data)} pages")

        # ── STEP 4: Cross-page analysis ─────────────────────────
        await publish_crawl_progress(crawl_id, "analyzing", "Running cross-page analysis...")

        # 4a: Duplicate content detection
        extracted = detect_duplicates(extracted)

        # 4b: Internal link graph analysis
        extracted = analyze_link_graph(extracted)

        # 4c: Canonical chain detection
        extracted = detect_canonical_chains(extracted)

        # 4d: Redirect chain detection
        extracted = detect_redirect_chains(extracted)

        # 4e: hreflang validation
        extracted = validate_hreflang(extracted)

        # 4f: Orphan page detection (in sitemap but not linked)
        sitemap_url_set = set(sitemap_urls)
        crawled_url_set = {p["url"] for p in extracted}
        orphan_pages = sitemap_url_set - crawled_url_set

        # ── STEP 5: Calculate scores ────────────────────────────
        for page in extracted:
            page["seo_score"] = calculate_page_score(page)

        site_score = calculate_site_score(extracted)

        # ── STEP 6: Generate issues ─────────────────────────────
        issue_gen = IssueGenerator()
        issues = issue_gen.generate(extracted, orphan_pages=list(orphan_pages))

        # ── STEP 7: Save everything to database ─────────────────
        await publish_crawl_progress(crawl_id, "saving", "Saving results...")

        await db.bulk_insert_pages(crawl_id, site_id, site.org_id, extracted)
        await db.bulk_insert_issues(crawl_id, site_id, site.org_id, issues)

        # ── STEP 8: Trigger AI analysis (async) ─────────────────
        from workers.tasks.ai_analysis import run_ai_analysis
        run_ai_analysis.delay(crawl_id, site_id)

        # ── STEP 9: Complete crawl ──────────────────────────────
        duration_ms = int((time.time() - start_time) * 1000)
        await db.update_crawl(
            crawl_id,
            status="completed",
            completed_at=datetime.now(timezone.utc),
            pages_crawled=len(extracted),
            issues_found=len(issues),
            seo_score=site_score,
            duration_ms=duration_ms,
        )

        await publish_crawl_progress(crawl_id, "completed",
            f"Crawl complete! {len(extracted)} pages, {len(issues)} issues found.")

        # Update site's last_crawled_at
        await db.update_site(site_id, last_crawled_at=datetime.now(timezone.utc))

    except Exception as e:
        logger.error("crawl_failed", site_id=site_id, error=str(e))
        await db.update_crawl(crawl_id, status="failed",
                              error_message=str(e),
                              completed_at=datetime.now(timezone.utc))
        await publish_crawl_progress(crawl_id, "failed", f"Crawl failed: {str(e)}")
        raise


async def _tiered_crawl(site, queue, robots, crawl_id) -> list[dict]:
    """
    Crawl using the 3-layer fallback chain (Jina → Crawl4AI → ScrapFly).
    """
    # Initialize layers
    jina = JinaLayer(api_key=settings.JINA_API_KEY)
    crawl4ai = Crawl4AILayer(
        use_camoufox=True,
        max_pages=site.crawl_max_pages,
        crawl_delay=robots.get_crawl_delay(),
    )
    scrapfly = ScrapFlyLayer(
        api_key=settings.SCRAPFLY_API_KEY,
        budget_per_crawl=5000,
    )

    pages_data = []
    pages_processed = 0
    layer_stats = {"jina": 0, "crawl4ai": 0, "scrapfly": 0, "failed": 0}

    # First, try a site-wide deep crawl with Crawl4AI
    # This is faster than URL-by-URL for sites that allow it
    if site.crawl_max_pages <= 500:
        await publish_crawl_progress(crawl_id, "deep_crawl",
            "Attempting full site deep crawl...")

        async for page_result in crawl4ai.crawl_site(site.domain):
            pages_data.append({
                "url": page_result.url,
                "html": page_result.html,
                "status_code": page_result.status_code,
                "source": "crawl4ai",
            })
            layer_stats["crawl4ai"] += 1
            pages_processed += 1

            # Check if we got blocked
            if is_blocked_content(page_result.html):
                logger.info("deep_crawl_blocked", url=site.domain)
                break

            if pages_processed >= site.crawl_max_pages:
                break

    # If deep crawl didn't get enough pages, use URL-by-URL approach
    if len(pages_data) < queue.size * 0.5:
        remaining_urls = [u.url for u in queue._queue if u.url not in {p["url"] for p in pages_data}]

        for url in remaining_urls[:site.crawl_max_pages - len(pages_data)]:
            # Check robots.txt
            if not robots.is_allowed(url):
                continue

            # Respect crawl delay
            await asyncio.sleep(robots.get_crawl_delay())

            page_data = await _fetch_single_url(url, jina, crawl4ai, scrapfly, layer_stats)
            if page_data:
                pages_data.append(page_data)
            else:
                layer_stats["failed"] += 1

            pages_processed += 1
            if pages_processed % 20 == 0:
                await publish_crawl_progress(crawl_id, "crawling",
                    f"Crawled {pages_processed} pages...")

    logger.info("tiered_crawl_complete", site_id=str(site.id),
                total_pages=len(pages_data), stats=layer_stats)

    # Log ScrapFly usage
    scrapfly_usage = scrapfly.get_usage_report()
    logger.info("scrapfly_usage", **scrapfly_usage)

    return pages_data


async def _fetch_single_url(url, jina, crawl4ai, scrapfly, stats) -> dict | None:
    """Try each layer for a single URL, fall back on failure."""
    # Layer 1: Jina
    result = await jina.fetch_for_seo(url)
    if result and not is_blocked_content(result.get("html", "")):
        stats["jina"] += 1
        return result

    # Layer 2: Crawl4AI
    result = await crawl4ai.crawl_single(url)
    if result and not is_blocked_content(result.html):
        stats["crawl4ai"] += 1
        return {"url": result.url, "html": result.html,
                "status_code": result.status_code, "source": "crawl4ai"}

    # Layer 3: ScrapFly
    result = await scrapfly.fetch(url)
    if result and not is_blocked_content(result.get("html", "")):
        stats["scrapfly"] += 1
        return result

    return None
```

---

## 10. SEO SIGNAL EXTRACTOR — COMPLETE IMPLEMENTATION

```python
# packages/crawler/extractor.py
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import json
import re
import structlog

logger = structlog.get_logger()


class SEOExtractor:
    """
    Extract ALL SEO signals from raw HTML.
    This is the core data extraction engine — every field maps to the pages table.
    """

    def __init__(self, html: str, url: str):
        self.soup = BeautifulSoup(html, "lxml")
        self.url = url
        self.parsed_url = urlparse(url)
        self.base_domain = self.parsed_url.netloc

    def extract_all(self) -> dict:
        """Extract every SEO signal. Returns dict matching pages table columns."""
        return {
            # Meta
            **self._meta(),
            # Headings
            **self._headings(),
            # Links
            **self._links(),
            # Images
            **self._images(),
            # Schema
            **self._schema(),
            # Social
            **self._social(),
            # Technical
            **self._technical(),
            # Hreflang
            **self._hreflang(),
            # Security
            **self._security(),
            # Content
            **self._content(),
        }

    def _meta(self) -> dict:
        title_el = self.soup.find("title")
        title = title_el.get_text(strip=True) if title_el else None

        desc_el = self.soup.find("meta", attrs={"name": "description"})
        desc = desc_el.get("content", "").strip() if desc_el else None

        canonical_el = self.soup.find("link", attrs={"rel": "canonical"})
        canonical = canonical_el.get("href") if canonical_el else None

        robots_el = self.soup.find("meta", attrs={"name": "robots"})
        robots = robots_el.get("content") if robots_el else "index, follow"

        viewport_el = self.soup.find("meta", attrs={"name": "viewport"})
        has_viewport = viewport_el is not None

        # Detect duplicate meta tags (Yoast + Rank Math conflict)
        meta_descriptions = self.soup.find_all("meta", attrs={"name": "description"})
        duplicate_meta = len(meta_descriptions) > 1

        return {
            "title": title,
            "title_length": len(title) if title else 0,
            "meta_description": desc,
            "meta_description_length": len(desc) if desc else 0,
            "canonical_url": canonical,
            "robots_directive": robots,
            "has_viewport": has_viewport,
            "duplicate_meta_tags": duplicate_meta,
        }

    def _headings(self) -> dict:
        h1s = self.soup.find_all("h1")
        h2s = self.soup.find_all("h2")
        h3s = self.soup.find_all("h3")

        # Build heading structure for hierarchy analysis
        structure = []
        for tag in self.soup.find_all(re.compile(r'^h[1-6]$')):
            structure.append({
                "level": int(tag.name[1]),
                "text": tag.get_text(strip=True)[:100],
            })

        return {
            "h1_count": len(h1s),
            "h1_text": [h.get_text(strip=True) for h in h1s],
            "h2_count": len(h2s),
            "h3_count": len(h3s),
            "heading_structure": structure,
        }

    def _links(self) -> dict:
        links = self.soup.find_all("a", href=True)
        internal = []
        external = []
        broken_candidates = []

        for link in links:
            href = link["href"]
            parsed = urlparse(href)

            # Skip anchors, javascript, mailto
            if href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue

            if parsed.netloc in ("", self.base_domain):
                internal.append(href)
            else:
                external.append(href)

            # Detect potentially broken: no href or empty
            if not href.strip():
                broken_candidates.append(str(link))

        return {
            "internal_links_count": len(internal),
            "external_links_count": len(external),
            "broken_links_count": len(broken_candidates),
            "internal_links": internal[:200],  # Store for link graph analysis
        }

    def _images(self) -> dict:
        imgs = self.soup.find_all("img")
        missing_alt = [i for i in imgs if not i.get("alt")]
        large_images = []

        for img in imgs:
            # Detect large images via width/height attributes
            width = img.get("width")
            height = img.get("height")
            if width and height:
                try:
                    w = int(width)
                    h = int(height)
                    if w * h > 500000:  # Rough proxy for large
                        large_images.append(img.get("src", ""))
                except ValueError:
                    pass

        return {
            "images_count": len(imgs),
            "images_missing_alt": len(missing_alt),
            "images_large": len(large_images),
        }

    def _schema(self) -> dict:
        schemas = []
        types = []
        errors = []

        for script in self.soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                schemas.append(data)
                # Handle both single type and array of types
                if isinstance(data, dict):
                    t = data.get("@type", "")
                    if isinstance(t, list):
                        types.extend(t)
                    else:
                        types.append(t)
                elif isinstance(data, list):
                    for item in data:
                        t = item.get("@type", "") if isinstance(item, dict) else ""
                        if t:
                            types.append(t)
            except (json.JSONDecodeError, TypeError) as e:
                errors.append({"error": str(e), "snippet": (script.string or "")[:200]})

        return {
            "schema_types": types,
            "schema_valid": len(errors) == 0,
            "schema_errors": errors,
        }

    def _social(self) -> dict:
        def og(prop):
            el = self.soup.find("meta", attrs={"property": f"og:{prop}"})
            return el.get("content") if el else None

        def tw(name):
            el = self.soup.find("meta", attrs={"name": f"twitter:{name}"})
            return el.get("content") if el else None

        return {
            "og_title": og("title"),
            "og_description": og("description"),
            "og_image": og("image"),
            "twitter_card": tw("card"),
        }

    def _technical(self) -> dict:
        # Favicon
        favicon = (
            self.soup.find("link", attrs={"rel": "icon"}) or
            self.soup.find("link", attrs={"rel": "shortcut icon"}) or
            self.soup.find("link", attrs={"rel": "apple-touch-icon"})
        )

        # Web manifest
        manifest = self.soup.find("link", attrs={"rel": "manifest"})

        # Language attribute
        html_lang = self.soup.find("html")
        lang = html_lang.get("lang") if html_lang else None

        # Charset
        charset_el = self.soup.find("meta", charset=True)
        charset = charset_el.get("charset") if charset_el else None

        return {
            "favicon_present": favicon is not None,
            "web_manifest_present": manifest is not None,
            "html_lang": lang,
            "charset": charset,
        }

    def _hreflang(self) -> dict:
        tags = []
        for link in self.soup.find_all("link", attrs={"rel": "alternate", "hreflang": True}):
            tags.append({
                "lang": link.get("hreflang"),
                "href": link.get("href"),
            })

        # Check for x-default
        has_x_default = any(t["lang"] == "x-default" for t in tags)

        return {
            "hreflang_tags": tags,
            "hreflang_has_x_default": has_x_default,
            "hreflang_errors": [],  # Populated by cross-page validator
        }

    def _security(self) -> dict:
        # These are checked from HTTP headers, not HTML
        # But we can check for mixed content
        mixed_content = []
        if self.parsed_url.scheme == "https":
            for tag in self.soup.find_all(["img", "script", "link", "iframe"]):
                src = tag.get("src") or tag.get("href")
                if src and src.startswith("http://"):
                    mixed_content.append({"tag": tag.name, "url": src})

        return {
            "is_https": self.parsed_url.scheme == "https",
            "mixed_content_count": len(mixed_content),
            "mixed_content_items": mixed_content[:10],
        }

    def _content(self) -> dict:
        # Word count (from visible text only)
        text = self.soup.get_text(separator=" ", strip=True)
        words = text.split()
        word_count = len(words)

        # Content hash for duplicate detection (SimHash)
        content_hash = self._simhash(text.lower())

        return {
            "word_count": word_count,
            "content_hash": content_hash,
        }

    def _simhash(self, text: str, hash_bits: int = 64) -> str:
        """
        SimHash for near-duplicate detection.
        Similar content produces similar hashes.
        Hamming distance < 3 = likely duplicate.
        """
        import hashlib

        tokens = text.split()
        if not tokens:
            return "0" * 16

        vector = [0] * hash_bits
        for token in tokens:
            token_hash = int(hashlib.md5(token.encode()).hexdigest(), 16)
            for i in range(hash_bits):
                if token_hash & (1 << i):
                    vector[i] += 1
                else:
                    vector[i] -= 1

        fingerprint = 0
        for i in range(hash_bits):
            if vector[i] >= 0:
                fingerprint |= (1 << i)

        return format(fingerprint, '016x')
```

---

## 11. ISSUE GENERATOR — SIGNALS TO ISSUES

```python
# packages/crawler/issue_generator.py
from dataclasses import dataclass
from typing import Optional
import structlog

logger = structlog.get_logger()


@dataclass
class Issue:
    """A single SEO issue found during analysis."""
    page_id: str | None = None
    page_url: str = ""
    type: str = ""
    category: str = ""
    severity: str = ""
    impact_score: int = 0
    current_value: str = ""
    fix_type: str = "manual"
    proposed_fix: str | None = None
    proposed_fix_metadata: dict | None = None


class IssueGenerator:
    """
    Maps extracted SEO signals to actionable issues.
    Each issue has severity, impact score, and fix type.
    """

    # Severity thresholds
    CRITICAL = "critical"   # Directly harms rankings
    HIGH = "high"           # Significant impact on rankings
    MEDIUM = "medium"       # Moderate impact
    LOW = "low"             # Minor improvement opportunity

    def generate(self, pages: list[dict], orphan_pages: list[str] | None = None) -> list[Issue]:
        """Generate issues from extracted page data."""
        issues = []

        for page in pages:
            issues.extend(self._check_meta(page))
            issues.extend(self._check_headings(page))
            issues.extend(self._check_images(page))
            issues.extend(self._check_links(page))
            issues.extend(self._check_schema(page))
            issues.extend(self._check_social(page))
            issues.extend(self._check_performance(page))
            issues.extend(self._check_technical(page))
            issues.extend(self._check_content(page))
            issues.extend(self._check_hreflang(page))
            issues.extend(self._check_duplicates(page))
            issues.extend(self._check_canonical(page))

        # Orphan pages (in sitemap but not linked)
        if orphan_pages:
            for url in orphan_pages:
                issues.append(Issue(
                    page_url=url,
                    type="orphan_page",
                    category="technical",
                    severity=self.HIGH,
                    impact_score=70,
                    current_value="Page exists in sitemap but has no internal links",
                    fix_type="manual",
                ))

        logger.info("issues_generated", total=len(issues),
                     critical=sum(1 for i in issues if i.severity == self.CRITICAL),
                     high=sum(1 for i in issues if i.severity == self.HIGH))
        return issues

    def _check_meta(self, page) -> list[Issue]:
        issues = []

        # Missing title
        if not page.get("title"):
            issues.append(Issue(
                page_url=page["url"], type="missing_title",
                category="content", severity=self.CRITICAL, impact_score=95,
                current_value="No <title> tag found",
                fix_type="semi_auto",
            ))

        # Title too short
        elif page.get("title_length", 0) < 30:
            issues.append(Issue(
                page_url=page["url"], type="title_too_short",
                category="content", severity=self.MEDIUM, impact_score=45,
                current_value=f'Title: "{page["title"]}" ({page["title_length"]} chars)',
                fix_type="semi_auto",
            ))

        # Title too long
        elif page.get("title_length", 0) > 60:
            issues.append(Issue(
                page_url=page["url"], type="title_too_long",
                category="content", severity=self.MEDIUM, impact_score=50,
                current_value=f'Title: "{page["title"]}" ({page["title_length"]} chars)',
                fix_type="semi_auto",
            ))

        # Missing meta description
        if not page.get("meta_description"):
            issues.append(Issue(
                page_url=page["url"], type="missing_meta_description",
                category="content", severity=self.HIGH, impact_score=80,
                current_value="No meta description found",
                fix_type="auto",
            ))

        # Meta description too short
        elif page.get("meta_description_length", 0) < 50:
            issues.append(Issue(
                page_url=page["url"], type="meta_description_too_short",
                category="content", severity=self.MEDIUM, impact_score=40,
                current_value=f'{page["meta_description"]}',
                fix_type="auto",
            ))

        # Meta description too long
        elif page.get("meta_description_length", 0) > 160:
            issues.append(Issue(
                page_url=page["url"], type="meta_description_too_long",
                category="content", severity=self.MEDIUM, impact_score=45,
                current_value=f'{page["meta_description"][:100]}... ({page["meta_description_length"]} chars)',
                fix_type="auto",
            ))

        # Duplicate meta tags (Yoast + Rank Math conflict)
        if page.get("duplicate_meta_tags"):
            issues.append(Issue(
                page_url=page["url"], type="duplicate_meta_tags",
                category="technical", severity=self.HIGH, impact_score=65,
                current_value="Multiple meta description tags found (possible plugin conflict)",
                fix_type="manual",
            ))

        # Missing canonical
        if not page.get("canonical_url"):
            issues.append(Issue(
                page_url=page["url"], type="missing_canonical",
                category="technical", severity=self.MEDIUM, impact_score=55,
                current_value="No canonical URL specified",
                fix_type="semi_auto",
            ))

        # noindex on important page
        robots = page.get("robots_directive", "")
        if "noindex" in robots.lower():
            issues.append(Issue(
                page_url=page["url"], type="noindex_detected",
                category="technical", severity=self.CRITICAL, impact_score=98,
                current_value=f'Robots directive: {robots}',
                fix_type="manual",
            ))

        return issues

    def _check_headings(self, page) -> list[Issue]:
        issues = []

        # Missing H1
        if page.get("h1_count", 0) == 0:
            issues.append(Issue(
                page_url=page["url"], type="missing_h1",
                category="content", severity=self.HIGH, impact_score=70,
                current_value="No H1 heading found",
                fix_type="semi_auto",
            ))

        # Multiple H1s
        elif page.get("h1_count", 0) > 1:
            issues.append(Issue(
                page_url=page["url"], type="multiple_h1",
                category="content", severity=self.MEDIUM, impact_score=35,
                current_value=f'{page.get("h1_count")} H1 tags found',
                fix_type="manual",
            ))

        return issues

    def _check_images(self, page) -> list[Issue]:
        issues = []
        missing_alt = page.get("images_missing_alt", 0)

        if missing_alt > 0:
            issues.append(Issue(
                page_url=page["url"], type="images_missing_alt",
                category="content", severity=self.MEDIUM, impact_score=40,
                current_value=f"{missing_alt} of {page.get('images_count', 0)} images missing alt text",
                fix_type="auto",
            ))

        if page.get("images_large", 0) > 0:
            issues.append(Issue(
                page_url=page["url"], type="large_images",
                category="performance", severity=self.MEDIUM, impact_score=50,
                current_value=f"{page['images_large']} images are very large",
                fix_type="manual",
            ))

        return issues

    def _check_links(self, page) -> list[Issue]:
        issues = []

        if page.get("broken_links_count", 0) > 0:
            issues.append(Issue(
                page_url=page["url"], type="broken_links",
                category="technical", severity=self.HIGH, impact_score=75,
                current_value=f"{page['broken_links_count']} broken links found",
                fix_type="manual",
            ))

        # Orphan page (no incoming links)
        if page.get("incoming_links_count", 0) == 0 and page.get("crawl_depth", 0) > 0:
            issues.append(Issue(
                page_url=page["url"], type="orphan_page",
                category="technical", severity=self.HIGH, impact_score=70,
                current_value="Page has no internal links pointing to it",
                fix_type="semi_auto",
            ))

        # Deep crawl depth
        if page.get("crawl_depth", 0) > 4:
            issues.append(Issue(
                page_url=page["url"], type="deep_crawl_depth",
                category="technical", severity=self.MEDIUM, impact_score=45,
                current_value=f"Page is {page['crawl_depth']} clicks from homepage",
                fix_type="manual",
            ))

        return issues

    def _check_schema(self, page) -> list[Issue]:
        issues = []

        if not page.get("schema_types"):
            issues.append(Issue(
                page_url=page["url"], type="missing_schema",
                category="schema", severity=self.MEDIUM, impact_score=50,
                current_value="No structured data (JSON-LD) found",
                fix_type="auto",
            ))

        if not page.get("schema_valid", True):
            issues.append(Issue(
                page_url=page["url"], type="invalid_schema",
                category="schema", severity=self.HIGH, impact_score=65,
                current_value=f"Schema validation errors: {page.get('schema_errors', [])}",
                fix_type="auto",
            ))

        return issues

    def _check_social(self, page) -> list[Issue]:
        issues = []

        if not page.get("og_title"):
            issues.append(Issue(
                page_url=page["url"], type="missing_og_tags",
                category="social", severity=self.LOW, impact_score=25,
                current_value="Missing Open Graph meta tags",
                fix_type="auto",
            ))

        if not page.get("og_image"):
            issues.append(Issue(
                page_url=page["url"], type="missing_og_image",
                category="social", severity=self.LOW, impact_score=20,
                current_value="Missing og:image tag",
                fix_type="auto",
            ))

        return issues

    def _check_performance(self, page) -> list[Issue]:
        issues = []

        lcp = page.get("lcp_ms")
        if lcp:
            if lcp > 4000:
                issues.append(Issue(
                    page_url=page["url"], type="poor_lcp",
                    category="performance", severity=self.HIGH, impact_score=70,
                    current_value=f"LCP: {lcp}ms (>4000ms = poor)",
                    fix_type="manual",
                ))
            elif lcp > 2500:
                issues.append(Issue(
                    page_url=page["url"], type="needs_improvement_lcp",
                    category="performance", severity=self.MEDIUM, impact_score=40,
                    current_value=f"LCP: {lcp}ms (2500-4000ms = needs improvement)",
                    fix_type="manual",
                ))

        cls = page.get("cls_score")
        if cls and cls > 0.25:
            issues.append(Issue(
                page_url=page["url"], type="poor_cls",
                category="performance", severity=self.HIGH, impact_score=60,
                current_value=f"CLS: {cls} (>0.25 = poor)",
                fix_type="manual",
            ))

        return issues

    def _check_technical(self, page) -> list[Issue]:
        issues = []

        if not page.get("is_https", True):
            issues.append(Issue(
                page_url=page["url"], type="not_https",
                category="technical", severity=self.CRITICAL, impact_score=90,
                current_value="Page is not served over HTTPS",
                fix_type="manual",
            ))

        if page.get("mixed_content_count", 0) > 0:
            issues.append(Issue(
                page_url=page["url"], type="mixed_content",
                category="technical", severity=self.HIGH, impact_score=60,
                current_value=f"{page['mixed_content_count']} HTTP resources on HTTPS page",
                fix_type="semi_auto",
            ))

        if not page.get("has_viewport", False):
            issues.append(Issue(
                page_url=page["url"], type="missing_viewport",
                category="technical", severity=self.CRITICAL, impact_score=85,
                current_value="Missing viewport meta tag (mobile-unfriendly)",
                fix_type="semi_auto",
            ))

        if not page.get("favicon_present", True):
            issues.append(Issue(
                page_url=page["url"], type="missing_favicon",
                category="technical", severity=self.LOW, impact_score=15,
                current_value="No favicon found",
                fix_type="manual",
            ))

        if not page.get("html_lang"):
            issues.append(Issue(
                page_url=page["url"], type="missing_html_lang",
                category="technical", severity=self.MEDIUM, impact_score=35,
                current_value="Missing html lang attribute",
                fix_type="semi_auto",
            ))

        return issues

    def _check_content(self, page) -> list[Issue]:
        issues = []
        word_count = page.get("word_count", 0)

        if word_count < 100:
            issues.append(Issue(
                page_url=page["url"], type="thin_content",
                category="content", severity=self.HIGH, impact_score=65,
                current_value=f"Only {word_count} words on page",
                fix_type="manual",
            ))

        return issues

    def _check_hreflang(self, page) -> list[Issue]:
        issues = []

        if page.get("hreflang_errors"):
            for error in page["hreflang_errors"]:
                issues.append(Issue(
                    page_url=page["url"], type="hreflang_error",
                    category="technical", severity=self.HIGH, impact_score=60,
                    current_value=error,
                    fix_type="manual",
                ))

        return issues

    def _check_duplicates(self, page) -> list[Issue]:
        issues = []

        if page.get("is_duplicate_of"):
            issues.append(Issue(
                page_url=page["url"], type="duplicate_content",
                category="content", severity=self.HIGH, impact_score=70,
                current_value=f"Near-duplicate of {page['is_duplicate_of']}",
                fix_type="semi_auto",
            ))

        if page.get("canonical_chain_length", 0) > 2:
            issues.append(Issue(
                page_url=page["url"], type="canonical_chain",
                category="technical", severity=self.HIGH, impact_score=60,
                current_value=f"Canonical chain of {page['canonical_chain_length']} hops",
                fix_type="manual",
            ))

        if page.get("redirect_chain_length", 0) > 1:
            issues.append(Issue(
                page_url=page["url"], type="redirect_chain",
                category="technical", severity=self.MEDIUM, impact_score=50,
                current_value=f"Redirect chain of {page['redirect_chain_length']} hops",
                fix_type="manual",
            ))

        return issues
```

---

## 12. SEO SCORE CALCULATOR

```python
# packages/crawler/score_calculator.py

def calculate_page_score(page: dict) -> int:
    """
    Calculate SEO score (0-100) for a single page.
    Weighted formula based on impact on rankings.
    """
    score = 100
    deductions = []

    # ── CRITICAL (deduct 25-30 each) ──────────────
    if not page.get("title"):
        score -= 30
        deductions.append("missing_title")
    if "noindex" in page.get("robots_directive", "").lower():
        score -= 30
        deductions.append("noindex")
    if not page.get("is_https", True):
        score -= 25
        deductions.append("not_https")
    if not page.get("has_viewport", True):
        score -= 25
        deductions.append("missing_viewport")

    # ── HIGH (deduct 15-20 each) ──────────────────
    if not page.get("meta_description"):
        score -= 20
        deductions.append("missing_meta_description")
    if not page.get("h1_count"):
        score -= 15
        deductions.append("missing_h1")
    if page.get("broken_links_count", 0) > 0:
        score -= min(20, page["broken_links_count"] * 5)
        deductions.append("broken_links")
    if page.get("incoming_links_count", 0) == 0:
        score -= 15
        deductions.append("orphan_page")
    if not page.get("schema_valid", True):
        score -= 15
        deductions.append("invalid_schema")
    if page.get("is_duplicate_of"):
        score -= 18
        deductions.append("duplicate_content")

    # ── MEDIUM (deduct 8-12 each) ─────────────────
    if page.get("title_length", 0) > 60 or page.get("title_length", 0) < 30:
        score -= 10
        deductions.append("title_length")
    if page.get("meta_description_length", 0) > 160 or page.get("meta_description_length", 0) < 50:
        score -= 8
        deductions.append("meta_description_length")
    if page.get("images_missing_alt", 0) > 0:
        score -= min(12, page["images_missing_alt"] * 2)
        deductions.append("images_missing_alt")
    if page.get("crawl_depth", 0) > 4:
        score -= 10
        deductions.append("deep_crawl_depth")
    lcp = page.get("lcp_ms", 0)
    if lcp > 4000:
        score -= 12
    elif lcp > 2500:
        score -= 6

    # ── LOW (deduct 3-5 each) ─────────────────────
    if not page.get("og_title"):
        score -= 3
    if not page.get("favicon_present", True):
        score -= 3
    if not page.get("html_lang"):
        score -= 5

    return max(0, min(100, score))


def calculate_site_score(pages: list[dict]) -> int:
    """
    Calculate overall site SEO score (0-100).
    Weighted average with penalty for critical issues.
    """
    if not pages:
        return 0

    # Average page score
    avg_score = sum(p.get("seo_score", 0) for p in pages) / len(pages)

    # Count critical issues
    critical_count = sum(
        1 for p in pages
        if p.get("seo_score", 100) < 30
    )
    critical_ratio = critical_count / len(pages)

    # Penalty: if >20% of pages are critical, dock the score
    if critical_ratio > 0.2:
        avg_score *= (1 - critical_ratio * 0.5)

    return max(0, min(100, int(avg_score)))
```

---

## 13. AI FIX ENGINE — CLAUDE-POWERED

```python
# packages/ai_engine/fix_engine.py
import anthropic
import json
import structlog
from typing import Optional

logger = structlog.get_logger()


class AIFixEngine:
    """
    Generate AI-powered fixes for SEO issues using Claude.
    Every fix includes confidence scoring and validation.
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5"):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def generate_fix(self, issue: dict, page_context: dict) -> dict | None:
        """Generate an AI fix for a single issue."""
        prompt = self._build_fix_prompt(issue, page_context)

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.3,  # Low temperature for consistent, factual output
                system=self._system_prompt(),
                messages=[{"role": "user", "content": prompt}],
            )

            fix_text = response.content[0].text.strip()
            parsed = self._parse_fix_response(fix_text, issue)

            # Run validation
            parsed["validation"] = await self._validate_fix(parsed, issue)

            # Content safety check
            parsed["safety_flags"] = self._check_content_safety(parsed, page_context)

            return parsed

        except Exception as e:
            logger.error("ai_fix_generation_failed", issue_type=issue["type"], error=str(e))
            return None

    def _system_prompt(self) -> str:
        return """You are an SEO expert AI assistant. You generate precise, implementable fixes for SEO issues.

RULES:
1. NEVER change content meaning — only optimize for search engines
2. NEVER include competitor brand names in generated content
3. NEVER make factual claims you cannot verify
4. ALWAYS keep titles under 60 characters
5. ALWAYS keep meta descriptions between 50-160 characters
6. ALWAYS generate valid HTML for the proposed fix
7. ALWAYS rate your confidence (0.0 to 1.0) for each fix
8. If you're not confident, say so — do NOT hallucinate

RESPONSE FORMAT (JSON):
{
  "proposed_fix": "the actual fix value",
  "fix_type": "auto|semi_auto|manual",
  "confidence": 0.85,
  "explanation": "Why this fix improves SEO",
  "implementation_hint": "How to apply this fix"
}"""

    def _build_fix_prompt(self, issue: dict, page_context: dict) -> str:
        return f"""Fix this SEO issue:

ISSUE TYPE: {issue['type']}
SEVERITY: {issue['severity']}
CURRENT VALUE: {issue['current_value']}

PAGE CONTEXT:
- URL: {page_context.get('url', '')}
- Title: {page_context.get('title', '')}
- H1: {page_context.get('h1_text', [''])[0] if page_context.get('h1_text') else ''}
- Word count: {page_context.get('word_count', 0)}
- Content snippet: {page_context.get('content_snippet', '')[:500]}

Generate the fix as JSON:"""

    def _parse_fix_response(self, response: str, issue: dict) -> dict:
        """Parse Claude's JSON response."""
        try:
            # Try to extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                parsed = json.loads(response[json_start:json_end])
                return {
                    "proposed_fix": parsed.get("proposed_fix", ""),
                    "fix_type": parsed.get("fix_type", issue.get("fix_type", "manual")),
                    "ai_confidence": min(1.0, max(0.0, float(parsed.get("confidence", 0.5)))),
                    "explanation": parsed.get("explanation", ""),
                    "implementation_hint": parsed.get("implementation_hint", ""),
                }
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: use raw response as proposed fix
        return {
            "proposed_fix": response,
            "fix_type": issue.get("fix_type", "manual"),
            "ai_confidence": 0.3,  # Low confidence for unparseable response
            "explanation": "AI response could not be structured",
        }

    async def _validate_fix(self, fix: dict, issue: dict) -> dict:
        """Validate the proposed fix before it's shown to the user."""
        validation = {"is_valid": True, "errors": []}

        proposed = fix.get("proposed_fix", "")
        issue_type = issue["type"]

        # Title length validation
        if issue_type in ("missing_title", "title_too_long", "title_too_short"):
            if len(proposed) > 60:
                validation["errors"].append(f"Title is {len(proposed)} chars — max 60")
            if len(proposed) < 10:
                validation["errors"].append("Title is too short (minimum 10 chars)")

        # Meta description length validation
        if issue_type in ("missing_meta_description", "meta_description_too_long", "meta_description_too_short"):
            if len(proposed) > 160:
                validation["errors"].append(f"Meta description is {len(proposed)} chars — max 160")
            if len(proposed) < 50:
                validation["errors"].append("Meta description is too short (minimum 50 chars)")

        # URL validation for canonical fixes
        if issue_type == "canonical_chain" and proposed:
            if not proposed.startswith(("http://", "https://")):
                validation["errors"].append("Canonical URL must be absolute")

        # Schema validation
        if issue_type in ("missing_schema", "invalid_schema"):
            try:
                json.loads(proposed)
            except json.JSONDecodeError:
                validation["errors"].append("Schema must be valid JSON")

        if validation["errors"]:
            validation["is_valid"] = False

        return validation

    def _check_content_safety(self, fix: dict, page_context: dict) -> list[str]:
        """Check for content safety issues in AI-generated fixes."""
        flags = []
        proposed = fix.get("proposed_fix", "").lower()

        # Medical/legal/financial content detection
        medical_terms = ["diagnosis", "treatment", "cure", "medication", "prescription"]
        legal_terms = ["lawsuit", "attorney", "legal advice", "court order"]
        financial_terms = ["investment advice", "guaranteed return", "stock pick"]

        for term in medical_terms:
            if term in proposed:
                flags.append("medical_content_detected")
                break
        for term in legal_terms:
            if term in proposed:
                flags.append("legal_content_detected")
                break
        for term in financial_terms:
            if term in proposed:
                flags.append("financial_content_detected")
                break

        return flags
```

---

## 14. FIX VERIFICATION + ROLLBACK

```python
# packages/ai_engine/verification.py
import structlog

logger = structlog.get_logger()


class FixVerifier:
    """
    Verify that applied fixes actually stuck.
    Re-fetch the page after CMS write and confirm change.
    """

    async def verify_fix(self, issue_id: str, site_id: str) -> dict:
        """
        After a fix is applied to a CMS:
        1. Wait 5 seconds (let cache settle)
        2. Re-fetch the page
        3. Check if the fix value is now present
        4. If not — flag as "fix verification failed"
        """
        import asyncio
        await asyncio.sleep(5)

        issue = await db.get_issue(issue_id)
        site = await db.get_site(site_id)

        # Re-fetch the page using the crawler
        from packages.crawler.layers.jina_layer import JinaLayer
        jina = JinaLayer()
        result = await jina.fetch_for_seo(issue.page_url)

        if not result:
            return {"verified": False, "reason": "Could not re-fetch page"}

        # Re-extract signals
        from packages.crawler.extractor import SEOExtractor
        signals = SEOExtractor(result["html"], issue.page_url).extract_all()

        # Check if the fix is present
        issue_type = issue.type
        proposed = issue.proposed_fix

        verified = False
        if issue_type == "missing_meta_description" and signals.get("meta_description"):
            verified = proposed.lower() in signals["meta_description"].lower()
        elif issue_type == "missing_title" and signals.get("title"):
            verified = proposed.lower() in signals["title"].lower()
        elif issue_type == "images_missing_alt":
            # Harder to verify — check if count decreased
            verified = signals.get("images_missing_alt", 999) < (issue.current_metadata or {}).get("missing_alt_count", 999)

        if verified:
            await db.update_issue(issue_id, verified_at=datetime.utcnow(), verified_score=signals.get("seo_score"))
            logger.info("fix_verified", issue_id=issue_id)
        else:
            await db.update_issue(issue_id, fix_status="verification_failed")
            logger.warning("fix_verification_failed", issue_id=issue_id)

        return {"verified": verified}
```

---

## 15. CRAWL PROGRESS + REAL-TIME UPDATES

```python
# apps/api/routers/crawl_progress.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json

router = APIRouter()


@router.get("/crawls/{crawl_id}/progress")
async def crawl_progress_stream(crawl_id: str):
    """
    SSE endpoint for real-time crawl progress.
    Frontend connects to this and receives events as the crawl runs.
    """
    async def event_generator():
        last_status = None
        while True:
            crawl = await db.get_crawl(crawl_id)
            if not crawl:
                yield f"data: {json.dumps({'error': 'crawl not found'})}\n\n"
                break

            event = {
                "status": crawl.status,
                "pages_crawled": crawl.pages_crawled,
                "pages_total": crawl.pages_total,
                "issues_found": crawl.issues_found,
                "seo_score": crawl.seo_score,
                "message": getattr(crawl, 'progress_message', ''),
            }

            if event != last_status:
                yield f"data: {json.dumps(event)}\n\n"
                last_status = event

            if crawl.status in ("completed", "failed"):
                yield f"data: {json.dumps({**event, 'done': True})}\n\n"
                break

            await asyncio.sleep(2)  # Poll every 2 seconds

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# Redis pub/sub alternative (better for production):
async def publish_crawl_progress(crawl_id: str, status: str, message: str):
    """Publish crawl progress to Redis channel."""
    import redis.asyncio as aioredis
    r = aioredis.from_url(settings.REDIS_URL)
    await r.publish(
        f"crawl:{crawl_id}:progress",
        json.dumps({"status": status, "message": message, "timestamp": time.time()}),
    )
```

---

## 16. DIAMOND FEATURES — REVENUE MULTIPLIERS

Based on deep market research, these features will make people **switch from competitors and pay more**:

### Diamond Feature 1: PREDICTIVE PRIORITY ENGINE (People will pay $50/mo extra for this)

**What it does:** Instead of showing 200 issues and saying "fix these," it says: "Fix THIS one first. It will improve your score by 12 points. Here's why."

```python
# packages/ai_engine/priority_engine.py
class PredictivePriorityEngine:
    """
    Ranks issues by expected impact on SEO score.
    Tells users EXACTLY what to fix first for maximum improvement.
    No SEO tool does this well — this is a diamond feature.
    """

    async def prioritize(self, issues: list[dict], site_score: int) -> list[dict]:
        """Sort issues by expected score improvement if fixed."""
        for issue in issues:
            # Calculate expected improvement
            base_impact = issue.get("impact_score", 0)

            # Adjust for diminishing returns at higher scores
            if site_score > 80:
                base_impact *= 0.5  # Hard to improve from 80+
            elif site_score < 40:
                base_impact *= 1.3  # Easy improvements at low scores

            # Adjust for fix type (auto-fixes are more valuable = less effort)
            effort_multiplier = {
                "auto": 1.5,       # Zero effort → most valuable
                "semi_auto": 1.2,  # One click
                "manual": 0.8,     # Requires work
            }.get(issue.get("fix_type", "manual"), 0.8)

            issue["priority_score"] = int(base_impact * effort_multiplier)
            issue["estimated_score_gain"] = self._estimate_gain(issue, site_score)

        return sorted(issues, key=lambda x: x.get("priority_score", 0), reverse=True)

    def _estimate_gain(self, issue: dict, current_score: int) -> int:
        """Estimate how many points fixing this issue would add."""
        impact = issue.get("impact_score", 0)
        # Rough heuristic: impact_score of 80 → ~8 points at score 50
        gain = int(impact * 0.1 * (1 - current_score / 120))
        return max(1, min(20, gain))
```

### Diamond Feature 2: GEO/AEO SCORING (No competitor has this)

**What it does:** Scores your page's likelihood of being cited by ChatGPT, Perplexity, and Google AI Overviews.

```python
# packages/crawler/geo_scorer.py
class GEOScorer:
    """
    Generative Engine Optimization scorer.
    Evaluates how likely a page is to be cited by AI answer engines.
    Based on Princeton GEO research (2024): structured data, Q&A format,
    entity clarity, fact density, citation-worthy content.

    THIS IS A DIAMOND FEATURE — no major SEO tool offers this.
    """

    def score(self, page: dict) -> dict:
        signals = {
            "has_faq_schema": self._check_faq_schema(page),
            "has_howto_schema": self._check_howto_schema(page),
            "entity_clarity": self._check_entity_clarity(page),
            "qa_formatting": self._check_qa_formatting(page),
            "fact_density": self._check_fact_density(page),
            "structured_data_richness": self._check_schema_richness(page),
            "direct_answers": self._check_direct_answers(page),
            "citation_worthiness": self._check_citation_worthiness(page),
        }

        # Weighted score (0-100)
        geo_score = (
            signals["has_faq_schema"] * 15 +
            signals["entity_clarity"] * 20 +
            signals["qa_formatting"] * 15 +
            signals["fact_density"] * 20 +
            signals["structured_data_richness"] * 15 +
            signals["direct_answers"] * 10 +
            signals["citation_worthiness"] * 5
        )

        return {
            "geo_score": min(100, geo_score),
            "signals": signals,
            "recommendation": self._generate_recommendation(signals, geo_score),
        }

    def _check_faq_schema(self, page) -> int:
        schemas = page.get("schema_types", [])
        return 100 if "FAQPage" in schemas else 0

    def _check_entity_clarity(self, page) -> int:
        """Check if the page clearly defines its main entity."""
        # Has Product, Organization, Person schema = clear entity
        schemas = page.get("schema_types", [])
        entity_types = {"Product", "Organization", "Person", "LocalBusiness",
                       "Article", "Service", "Course", "Event"}
        overlap = entity_types & set(schemas)
        return min(100, len(overlap) * 50)

    def _check_qa_formatting(self, page) -> int:
        """Check if page uses question-answer formatting."""
        h2s = page.get("heading_structure", [])
        question_patterns = ["how to", "what is", "why does", "when should", "where can"]
        question_count = sum(
            1 for h in h2s
            if any(p in h.get("text", "").lower() for p in question_patterns)
        )
        return min(100, question_count * 25)

    def _check_fact_density(self, page) -> int:
        """Higher word count with data = more citation-worthy."""
        word_count = page.get("word_count", 0)
        if word_count > 2000: return 80
        if word_count > 1000: return 60
        if word_count > 500: return 40
        return 20

    def _check_schema_richness(self, page) -> int:
        schemas = page.get("schema_types", [])
        return min(100, len(schemas) * 20)

    def _check_direct_answers(self, page) -> int:
        """Check if page provides direct answers (definition-style content)."""
        # This would need NLP analysis — simplified for now
        word_count = page.get("word_count", 0)
        h1 = page.get("h1_text", [""])[0] if page.get("h1_text") else ""
        # If H1 is a question and there's content, likely has a direct answer
        if any(h1.lower().startswith(p) for p in ["what is", "how to", "why"]):
            return 70 if word_count > 300 else 40
        return 30

    def _check_citation_worthiness(self, page) -> int:
        """Content with sources/data is more likely to be cited by AI."""
        html = page.get("raw_html", "")
        has_stats = any(tag in html for tag in ["<cite>", "<blockquote>", "source:", "according to"])
        return 80 if has_stats else 30

    def _generate_recommendation(self, signals: dict, score: int) -> str:
        if score < 30:
            return "Low AI visibility. Add FAQ schema, use question headings, and define your main entity with structured data."
        elif score < 60:
            return "Moderate AI visibility. Improve by adding FAQ content and clarifying your entity with schema markup."
        elif score < 80:
            return "Good AI visibility. Fine-tune by adding more Q&A sections and supporting data/citations."
        else:
            return "Excellent AI visibility. Your content is well-optimized for AI answer engines."
```

### Diamond Feature 3: COMPETITOR GAP ANALYSIS (Instant "aha" moment)

**What it does:** Crawl your top 3 competitors. Show exactly which keywords/features/content THEY have that YOU don't.

```python
# packages/crawler/competitor_gap.py
class CompetitorGapAnalyzer:
    """
    Compare your site against competitors.
    Shows: keywords they rank for that you don't,
    schema types they use, content they have, etc.
    Agencies LOVE this — instant value demonstration.
    """
    # Implementation: crawl competitor URLs, compare signals, generate gap report
    pass  # Full implementation in next phase
```

### Diamond Feature 4: WEEKLY SEO DIGEST (Retention machine)

**What it does:** Every Monday, send an email: "Your score went from 67→72. Here's what changed. Fix these 3 things this week."

**Why it's diamond:** People never cancel tools that send them weekly progress. It's the retention hack that Semrush and Ahrefs use.

---

## 17. DATABASE CHANGES FROM V3

### New Columns Needed

```sql
-- Add INP support (replaced FID as Core Web Vital)
ALTER TABLE pages ADD COLUMN inp_ms INTEGER;
ALTER TABLE snippet_events ADD COLUMN inp_ms INTEGER;

-- Add crawl source tracking
ALTER TABLE pages ADD COLUMN crawl_source TEXT DEFAULT 'crawler';
-- Values: 'jina' | 'crawl4ai' | 'scrapfly' | 'wordpress_api' | 'shopify_api' | 'snippet'

-- Add GEO/AEO score
ALTER TABLE pages ADD COLUMN geo_score SMALLINT;

-- Add snippet field data columns (merge with lab data)
ALTER TABLE pages ADD COLUMN field_lcp_ms INTEGER;
ALTER TABLE pages ADD COLUMN field_inp_ms INTEGER;
ALTER TABLE pages ADD COLUMN field_cls_score NUMERIC(4,3);
ALTER TABLE pages ADD COLUMN field_ttfb_ms INTEGER;
ALTER TABLE pages ADD COLUMN data_source TEXT DEFAULT 'lab';
-- Values: 'lab' (crawler) | 'field' (snippet) | 'merged' (both)

-- Add cost tracking per crawl
ALTER TABLE crawls ADD COLUMN scrapfly_credits_used INTEGER DEFAULT 0;
ALTER TABLE crawls ADD COLUMN crawl_layer_stats JSONB;
-- Example: {"jina": 45, "crawl4ai": 120, "scrapfly": 15, "failed": 5}

-- Add issue priority (for Predictive Priority Engine)
ALTER TABLE issues ADD COLUMN priority_score INTEGER DEFAULT 0;
ALTER TABLE issues ADD COLUMN estimated_score_gain INTEGER DEFAULT 0;
ALTER TABLE issues ADD COLUMN safety_flags TEXT[] DEFAULT '{}';

-- Add orphan page tracking
ALTER TABLE crawls ADD COLUMN orphan_pages_count INTEGER DEFAULT 0;

-- Add snippet event batching support
ALTER TABLE snippet_events ADD COLUMN session_id TEXT;
ALTER TABLE snippet_events ADD COLUMN batch_id TEXT;

-- New indexes for performance
CREATE INDEX idx_pages_site_crawl ON pages(site_id, crawl_id);
CREATE INDEX idx_issues_site_severity ON issues(site_id, severity);
CREATE INDEX idx_issues_type ON issues(type);
CREATE INDEX idx_snippet_events_url_time ON snippet_events(site_id, page_url, created_at DESC);
CREATE INDEX idx_crawls_status ON crawls(status);
```

---

## 18. COMPLETE FILE-BY-FILE IMPLEMENTATION

### Files to Create (In Order)

```
packages/crawler/
├── __init__.py
├── pre_crawl/
│   ├── __init__.py
│   ├── robots.py           # RobotsParser class
│   ├── sitemap.py          # SitemapParser class
│   └── priority_queue.py   # CrawlPriorityQueue class
├── layers/
│   ├── __init__.py
│   ├── jina_layer.py       # JinaLayer class
│   ├── crawl4ai_layer.py   # Crawl4AILayer class
│   ├── scrapfly_layer.py   # ScrapFlyLayer class
│   ├── cms_layer.py        # CMSReader class
│   └── anti_detect.py      # is_blocked_content, should_fallback_to_scrapfly
├── extractor.py             # SEOExtractor class (all signals)
├── analyzer.py              # Cross-page analysis (duplicates, links, chains)
├── issue_generator.py       # IssueGenerator class
├── score_calculator.py      # calculate_page_score, calculate_site_score
├── geo_scorer.py            # GEOScorer class (diamond feature)
└── competitor_gap.py        # CompetitorGapAnalyzer (diamond feature)

packages/ai_engine/
├── __init__.py
├── fix_engine.py            # AIFixEngine class
├── verification.py          # FixVerifier class
└── priority_engine.py       # PredictivePriorityEngine (diamond feature)

packages/snippet/
├── autoseo-snippet.js       # Client-side JS snippet (deployed to CDN)
└── snippet.config.js        # Build config for minification

workers/tasks/
├── crawl.py                 # run_site_crawl Celery task
└── ai_analysis.py           # run_ai_analysis Celery task

apps/api/routers/
├── snippet.py               # /snippet/collect endpoint
└── crawl_progress.py        # SSE progress endpoint
```

### Cross-Page Analyzer

```python
# packages/crawler/analyzer.py
import structlog
from collections import defaultdict

logger = structlog.get_logger()


def detect_duplicates(pages: list[dict]) -> list[dict]:
    """
    Detect near-duplicate pages using SimHash.
    Hamming distance < 3 between two hashes = likely duplicate.
    """
    HASH_BIT_LENGTH = 64
    DUPLICATE_THRESHOLD = 3

    for i, page_a in enumerate(pages):
        if not page_a.get("content_hash"):
            continue

        hash_a = int(page_a["content_hash"], 16)

        for j, page_b in enumerate(pages):
            if i >= j or not page_b.get("content_hash"):
                continue

            hash_b = int(page_b["content_hash"], 16)

            # Calculate Hamming distance
            hamming = bin(hash_a ^ hash_b).count('1')

            if hamming < DUPLICATE_THRESHOLD:
                page_a["is_duplicate_of"] = page_b["url"]
                page_b["is_duplicate_of"] = page_a["url"]
                logger.info("duplicate_detected",
                           url_a=page_a["url"], url_b=page_b["url"],
                           hamming_distance=hamming)

    return pages


def analyze_link_graph(pages: list[dict]) -> list[dict]:
    """
    Build internal link graph and calculate incoming_links_count per page.
    Orphan pages (0 incoming links) are a critical SEO issue.
    """
    # Build a map of URL → incoming link count
    incoming = defaultdict(int)
    url_set = {p["url"] for p in pages}

    for page in pages:
        for link in page.get("internal_links", []):
            # Normalize link to match our URL format
            if link in url_set:
                incoming[link] += 1

    # Assign incoming link counts
    for page in pages:
        page["incoming_links_count"] = incoming.get(page["url"], 0)

    return pages


def detect_canonical_chains(pages: list[dict]) -> list[dict]:
    """
    Detect canonical chains: A→B→C where A canonicalizes to B which canonicalizes to C.
    Google only follows 2 hops — chains > 2 are broken.
    Also detect circular canonicals: A→B→A.
    """
    # Build canonical map: URL → canonical URL
    canonical_map = {}
    for page in pages:
        if page.get("canonical_url"):
            canonical_map[page["url"]] = page["canonical_url"]

    # Follow chains
    for page in pages:
        chain = []
        current = page["url"]
        visited = set()

        while current in canonical_map and current not in visited:
            visited.add(current)
            next_url = canonical_map[current]
            chain.append(next_url)
            current = next_url

            if len(chain) > 5:  # Safety: prevent infinite loops
                break

        if len(chain) > 1:
            page["canonical_chain"] = chain
            page["canonical_chain_length"] = len(chain)

            # Circular detection
            if current in visited:
                page["canonical_chain_circular"] = True
        else:
            page["canonical_chain_length"] = 0

    return pages


def detect_redirect_chains(pages: list[dict]) -> list[dict]:
    """Detect redirect chains from redirect_chain JSONB data."""
    for page in pages:
        chain = page.get("redirect_chain", [])
        if isinstance(chain, list) and len(chain) > 1:
            page["redirect_chain_length"] = len(chain)

            # Check for redirect loops
            urls_in_chain = [hop.get("url", "") for hop in chain if isinstance(hop, dict)]
            if len(urls_in_chain) != len(set(urls_in_chain)):
                page["redirect_chain_loop"] = True
        else:
            page["redirect_chain_length"] = 0

    return pages


def validate_hreflang(pages: list[dict]) -> list[dict]:
    """
    Validate hreflang bidirectional linking.
    If page EN links to page FR with hreflang="fr",
    then page FR MUST link back to page EN with hreflang="en".
    Missing return tags are a common and critical international SEO issue.
    """
    # Build hreflang map
    hreflang_map = {}  # (url, lang) → target_url
    for page in pages:
        for tag in page.get("hreflang_tags", []):
            hreflang_map[(page["url"], tag["lang"])] = tag["href"]

    # Validate bidirectional linking
    for page in pages:
        errors = []
        for tag in page.get("hreflang_tags", []):
            target_url = tag["href"]
            source_lang = tag["lang"]

            # Check if target links back
            expected_return = ("en" if source_lang != "en" else source_lang)
            return_tag = hreflang_map.get((target_url, "en"))

            if not return_tag or return_tag != page["url"]:
                errors.append(
                    f"Missing return tag: {target_url} does not link back to {page['url']} with hreflang='en'"
                )

        if errors:
            page["hreflang_errors"] = errors

    return pages
```

---

## 19. TESTING STRATEGY

### Test Sites for Crawl Validation

```
Test your crawler against these 5 site types:

1. Static HTML site (e.g., a simple blog)
   → Should be handled by Layer 1 (Jina) alone

2. WordPress site with Yoast
   → Layer 1 or Layer 5 (CMS API if connected)

3. React SPA (e.g., a Next.js commerce site)
   → Layer 2 (Crawl4AI) needed for JS rendering

4. Cloudflare-protected site
   → Layer 3 (ScrapFly) fallback

5. Shopify store
   → Layer 5 (CMS API) if connected, else Layer 1-3
```

### Integration Test Template

```python
# tests/test_crawler.py
import pytest
from packages.crawler.pre_crawl.robots import RobotsParser
from packages.crawler.pre_crawl.sitemap import SitemapParser
from packages.crawler.layers.jina_layer import JinaLayer
from packages.crawler.extractor import SEOExtractor
from packages.crawler.issue_generator import IssueGenerator
from packages.crawler.score_calculator import calculate_page_score


@pytest.mark.asyncio
async def test_robots_parser():
    robots = RobotsParser("https://example.com")
    await robots.fetch()
    assert robots.is_allowed("https://example.com/") == True


@pytest.mark.asyncio
async def test_sitemap_parser():
    parser = SitemapParser("https://example.com")
    result = await parser.discover_all()
    assert result.total_urls > 0


@pytest.mark.asyncio
async def test_jina_layer():
    jina = JinaLayer()
    result = await jina.fetch("https://example.com")
    assert result is not None
    assert result.title != ""


def test_seo_extractor():
    html = """
    <html lang="en">
    <head>
        <title>Test Page</title>
        <meta name="description" content="A test page for SEO">
        <link rel="canonical" href="https://example.com/test">
    </head>
    <body>
        <h1>Main Heading</h1>
        <p>Some content here with enough words to not be thin content.</p>
        <img src="test.jpg" alt="Test image">
        <a href="/about">About</a>
    </body>
    </html>
    """
    extractor = SEOExtractor(html, "https://example.com/test")
    signals = extractor.extract_all()

    assert signals["title"] == "Test Page"
    assert signals["meta_description"] == "A test page for SEO"
    assert signals["canonical_url"] == "https://example.com/test"
    assert signals["h1_count"] == 1
    assert signals["images_count"] == 1
    assert signals["images_missing_alt"] == 0


def test_issue_generator():
    pages = [{
        "url": "https://example.com/test",
        "title": None,
        "title_length": 0,
        "meta_description": None,
        "h1_count": 0,
        "seo_score": 20,
    }]
    gen = IssueGenerator()
    issues = gen.generate(pages)
    assert any(i.type == "missing_title" for i in issues)
    assert any(i.type == "missing_meta_description" for i in issues)


def test_page_score():
    perfect_page = {
        "title": "Great Title",
        "title_length": 40,
        "meta_description": "A perfect meta description for SEO optimization purposes",
        "meta_description_length": 55,
        "h1_count": 1,
        "is_https": True,
        "has_viewport": True,
        "schema_valid": True,
        "incoming_links_count": 5,
    }
    score = calculate_page_score(perfect_page)
    assert score >= 90  # Perfect page should score high

    bad_page = {
        "title": None,
        "title_length": 0,
        "robots_directive": "noindex",
        "is_https": False,
        "has_viewport": False,
    }
    score = calculate_page_score(bad_page)
    assert score <= 20  # Bad page should score low
```

---

## 20. CODING CHECKLIST — EXECUTE IN ORDER

### Step 1: Pre-Crawl Intelligence (Day 1-2)
```
[ ] Create packages/crawler/ directory structure
[ ] Implement RobotsParser (packages/crawler/pre_crawl/robots.py)
[ ] Implement SitemapParser (packages/crawler/pre_crawl/sitemap.py)
[ ] Implement CrawlPriorityQueue (packages/crawler/pre_crawl/priority_queue.py)
[ ] Test with 3 real domains (one with robots.txt, one without, one with sitemap index)
[ ] Run database migration: add new columns from Section 17
```

### Step 2: Crawl Layers (Day 3-7)
```
[ ] Implement JinaLayer (packages/crawler/layers/jina_layer.py)
[ ] Implement anti_detect utilities (packages/crawler/layers/anti_detect.py)
[ ] Install Camoufox: pip install camoufox && python -m camoufox fetch
[ ] Implement Crawl4AILayer with Camoufox CDP (packages/crawler/layers/crawl4ai_layer.py)
[ ] Test Crawl4AI + Camoufox on a Cloudflare-protected site
[ ] Implement ScrapFlyLayer with budget tracking (packages/crawler/layers/scrapfly_layer.py)
[ ] Test ScrapFly on a known blocked site
[ ] Implement CMSReader for WordPress (packages/crawler/layers/cms_layer.py)
[ ] Test WordPress API read with a real site
```

### Step 3: SEO Extraction (Day 8-10)
```
[ ] Implement SEOExtractor (packages/crawler/extractor.py)
[ ] Test with 10 different HTML samples covering all signals
[ ] Implement cross-page analyzers (packages/crawler/analyzer.py)
  [ ] detect_duplicates (SimHash)
  [ ] analyze_link_graph
  [ ] detect_canonical_chains
  [ ] detect_redirect_chains
  [ ] validate_hreflang
```

### Step 4: Issue Generation + Scoring (Day 11-12)
```
[ ] Implement IssueGenerator (packages/crawler/issue_generator.py)
[ ] Implement calculate_page_score (packages/crawler/score_calculator.py)
[ ] Implement calculate_site_score
[ ] Test scoring with known pages (compare against Lighthouse SEO score)
```

### Step 5: Crawl Orchestrator (Day 13-15)
```
[ ] Implement run_site_crawl Celery task (workers/tasks/crawl.py)
[ ] Implement SSE crawl progress endpoint (apps/api/routers/crawl_progress.py)
[ ] Wire up frontend crawl progress UI
[ ] Test full crawl on 5 different sites:
  [ ] Static HTML blog
  [ ] WordPress with Yoast
  [ ] React SPA
  [ ] Cloudflare-protected site
  [ ] Shopify store
[ ] Log crawl layer statistics (jina vs crawl4ai vs scrapfly usage)
```

### Step 6: JS Snippet (Day 16-18)
```
[ ] Complete enhanced JS snippet (packages/snippet/autoseo-snippet.js)
[ ] Build /snippet/collect endpoint (apps/api/routers/snippet.py)
[ ] Deploy snippet to Cloudflare CDN (or R2 + Cloudflare Workers)
[ ] Test snippet on a test page with all features:
  [ ] Meta data collection
  [ ] Core Web Vitals (LCP, INP, CLS, TTFB)
  [ ] SPA navigation detection
  [ ] Error tracking
  [ ] Broken resource detection
[ ] Create one-line install instructions for clients
```

### Step 7: AI Fix Engine (Day 19-22)
```
[ ] Implement AIFixEngine (packages/ai_engine/fix_engine.py)
[ ] Design and test Claude prompts for each issue type
[ ] Implement validation pipeline
[ ] Implement content safety checker
[ ] Implement FixVerifier (packages/ai_engine/verification.py)
[ ] Implement run_ai_analysis Celery task (workers/tasks/ai_analysis.py)
[ ] Test AI fixes on 10 real SEO issues
```

### Step 8: Diamond Features (Day 23-28)
```
[ ] Implement PredictivePriorityEngine (packages/ai_engine/priority_engine.py)
[ ] Implement GEOScorer (packages/crawler/geo_scorer.py)
[ ] Add geo_score to pages table and extractor output
[ ] Test GEO scoring on 20 different pages
[ ] Add priority_score and estimated_score_gain to issues
```

### Step 9: Integration + Testing (Day 29-30)
```
[ ] End-to-end test: add site → crawl → see issues → AI fixes → verify
[ ] Test crawl on 10 different sites (various CMS types and protections)
[ ] Verify database records match expectations
[ ] Test SSE progress updates in frontend
[ ] Test snippet data flowing into dashboard
[ ] Write 30+ unit tests
[ ] Write 10+ integration tests
[ ] Monitor ScrapFly credit usage and adjust budget
```

---

## QUICK REFERENCE: LAYER SUCCESS RATES

| Layer | Tool | Success Rate | Cost | When to Use |
|-------|------|-------------|------|-------------|
| 5 | CMS API | 99% | Free | WordPress/Shopify connected |
| 4 | JS Snippet | 99% (field data) | Free | Client installed snippet |
| 1 | Jina Reader | 85% | Free | Static sites, first attempt |
| 2 | Crawl4AI + Camoufox | 60-70% | Free | JS-heavy sites |
| 3 | ScrapFly | 95% | $0.03-0.05/page | Cloudflare-protected sites |

## COST ESTIMATE PER 1000-PAGE CRAWL

| Scenario | Cost |
|----------|------|
| All Jina (no blocks) | $0.00 |
| 50% Jina + 50% Crawl4AI | $0.00 |
| 80% Jina + 15% Crawl4AI + 5% ScrapFly | ~$1.50 |
| All ScrapFly (worst case) | ~$30-50 |

**Average cost per crawl: $0.50 - $3.00** depending on site protection level.

---

## ANTI-HALLUCINATION GUARD

The following items in this plan are based on **verified research** (April 2026):
- ✅ Crawl4AI v0.8.6 API (verified from official docs)
- ✅ Camoufox CDP integration method (verified from GitHub)
- ✅ ScrapFly pricing (verified from website)
- ✅ Jina Reader API (verified from GitHub docs)
- ✅ Core Web Vitals INP replacement (confirmed March 2024)
- ✅ Anti-bot detection landscape (verified from multiple sources)

The following items are **estimated** and may need adjustment:
- ⚠️ Crawl4AI + Camoufox success rate (60-70% — needs real-world testing)
- ⚠️ ScrapFly cost per page (varies by site difficulty)
- ⚠️ GEO scoring signals (based on Princeton research, needs validation)
- ⚠️ Timeline estimates (may vary by developer experience)
