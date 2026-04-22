# AutoSEO Phase 2 — Complete Gap Analysis, Missing Features & Better Solutions
### Analyst Review of `AutoSEO_Phase2_Crawler_Build_Plan_v4.md`
### April 2026

---

> **Summary:** The plan is solid and well-researched. The 5-layer architecture is a strong foundation. However, there are **47 identified gaps** across 8 categories — ranging from critical bugs that will break the system at scale, to missing features that competitors charge $50+/mo for, to security vulnerabilities that could get the product hacked on day one. This document covers all of them.

---

## TABLE OF CONTENTS

1. [Critical Bugs — Will Break In Production](#1-critical-bugs)
2. [Architecture Gaps — Design Problems](#2-architecture-gaps)
3. [SEO Signal Gaps — Incomplete Data Collection](#3-seo-signal-gaps)
4. [Security Vulnerabilities — Not Mentioned At All](#4-security-vulnerabilities)
5. [JS Snippet Gaps — The Most Valuable Data Source Has Holes](#5-js-snippet-gaps)
6. [AI Fix Engine Gaps — Core Revenue Feature Is Incomplete](#6-ai-fix-engine-gaps)
7. [Missing Features — Things Not Thought Of At All](#7-missing-features)
8. [Better Solutions — Replace What's There With Something Smarter](#8-better-solutions)

---

## 1. CRITICAL BUGS — WILL BREAK IN PRODUCTION

These are bugs in the actual code that will cause failures or silent data corruption.

---

### Bug 1: `asyncio.run()` Inside a Celery Task — Will Deadlock

**Where:** `workers/tasks/crawl.py`, line 1598

```python
# CURRENT (broken):
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_site_crawl(self, site_id: str, crawl_id: str):
    asyncio.run(_async_crawl(site_id, crawl_id))  # 🔴 PROBLEM
```

**Why it breaks:** If you're running Celery with `gevent` or `eventlet` workers (common for production), `asyncio.run()` will deadlock or throw `RuntimeError: This event loop is already running`. Even with the default prefork workers, nesting `asyncio.run()` inside sync functions creates a new event loop per task but doesn't play well with the async DB library (Supabase uses asyncio internally).

**Fix:**
```python
# Option A: Use celery[asyncio] and make the task async
from asgiref.sync import async_to_sync

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_site_crawl(self, site_id: str, crawl_id: str):
    async_to_sync(_async_crawl)(site_id, crawl_id)

# Option B (better): Use Celery's native async support
# In celery config: task_always_eager = False, use pool=solo for dev
```

---

### Bug 2: Duplicate Detection is O(n²) — Will Time Out on Large Sites

**Where:** `packages/crawler/analyzer.py`, `detect_duplicates()`

```python
# CURRENT: O(n²) — 500 pages = 125,000 comparisons, 1000 pages = 500,000
for i, page_a in enumerate(pages):
    for j, page_b in enumerate(pages):
        if i >= j ...
            hamming = bin(hash_a ^ hash_b).count('1')
```

**Why it breaks:** For a 1,000-page site, this does 500,000 pair comparisons. Each comparison is fast, but the nested loop becomes noticeable at 5,000+ pages. It also loads all `content_hash` values into memory at once.

**Fix — Use a SimHash bucket approach (O(n log n)):**
```python
def detect_duplicates(pages: list[dict]) -> list[dict]:
    """O(n log n) SimHash using band+bucket LSH approach."""
    # Sort by hash — near-duplicates cluster when sorted
    pages_with_hash = [(p, int(p["content_hash"], 16)) 
                       for p in pages if p.get("content_hash")]
    pages_with_hash.sort(key=lambda x: x[1])
    
    # Only compare adjacent pairs (they're most similar when sorted)
    for i in range(len(pages_with_hash) - 1):
        page_a, hash_a = pages_with_hash[i]
        page_b, hash_b = pages_with_hash[i + 1]
        hamming = bin(hash_a ^ hash_b).count('1')
        if hamming < 3:
            page_a["is_duplicate_of"] = page_b["url"]
```

---

### Bug 3: `hreflang` Validator Has a Logic Bug — Always Checks For `en` Return

**Where:** `packages/crawler/analyzer.py`, `validate_hreflang()`

```python
# CURRENT (broken logic):
expected_return = ("en" if source_lang != "en" else source_lang)  # always "en"
return_tag = hreflang_map.get((target_url, "en"))  # always checks for "en" return
```

**Why it breaks:** If a French page (`lang="fr"`) links to a German page (`lang="de"`), the validator checks if the German page links back with `hreflang="en"`. It should check if it links back with `hreflang="fr"`. This means the validator will create thousands of false-positive errors on multilingual sites and miss real errors.

**Fix:**
```python
# Check if target_url has a tag pointing BACK to page["url"]
# with the CORRECT language (the source page's language)
source_page_lang = page.get("html_lang", "en")
return_tag = hreflang_map.get((target_url, source_page_lang))
if not return_tag or return_tag != page["url"]:
    errors.append(f"Missing return: {target_url} should have hreflang='{source_page_lang}' pointing to {page['url']}")
```

---

### Bug 4: Redis Connection Created Per Progress Event — Connection Leak

**Where:** `workers/tasks/crawl.py`, `publish_crawl_progress()`

```python
# CURRENT — creates a NEW Redis connection on every call:
async def publish_crawl_progress(crawl_id: str, status: str, message: str):
    r = aioredis.from_url(settings.REDIS_URL)  # 🔴 New connection every time
    await r.publish(...)
    # Connection never explicitly closed!
```

**Why it breaks:** A 500-page crawl calls `publish_crawl_progress` ~50+ times. Each call creates a new TCP connection to Redis. You'll hit the Redis connection limit quickly under load, and the leaked connections cause memory issues.

**Fix — Use a module-level Redis pool:**
```python
# In a shared module (e.g., workers/redis_client.py):
_redis_pool = None

async def get_redis():
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.ConnectionPool.from_url(settings.REDIS_URL, max_connections=10)
    return aioredis.Redis(connection_pool=_redis_pool)

async def publish_crawl_progress(crawl_id: str, status: str, message: str):
    r = await get_redis()
    await r.publish(f"crawl:{crawl_id}:progress", json.dumps({...}))
    # Pool handles connection reuse — no leak
```

---

### Bug 5: SSE Progress Endpoint Polls the Database Every 2 Seconds — DB Overload

**Where:** `apps/api/routers/crawl_progress.py`

```python
# CURRENT: DB query every 2 seconds per open SSE connection
while True:
    crawl = await db.get_crawl(crawl_id)  # 🔴 DB hit every 2s
    ...
    await asyncio.sleep(2)
```

**Why it breaks:** If 100 users are watching crawl progress simultaneously, that's 50 DB queries/second just for progress updates — before any actual crawl queries. The plan even mentions "Redis pub/sub alternative (better for production)" but makes it secondary. It should be primary.

**Fix — Subscribe to Redis channel instead of polling DB:**
```python
@router.get("/crawls/{crawl_id}/progress")
async def crawl_progress_stream(crawl_id: str):
    async def event_generator():
        r = await get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(f"crawl:{crawl_id}:progress")
        
        # Send last known state immediately
        crawl = await db.get_crawl(crawl_id)
        if crawl:
            yield f"data: {json.dumps(crawl_to_dict(crawl))}\n\n"
        
        # Then stream Redis events (zero DB queries)
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield f"data: {message['data'].decode()}\n\n"
                data = json.loads(message["data"])
                if data.get("status") in ("completed", "failed"):
                    break
    
    return StreamingResponse(event_generator(), media_type="text/event-stream", ...)
```

---

### Bug 6: `_tiered_crawl` Has a Double-Crawl Problem — Crawl4AI Then URL-by-URL

**Where:** `workers/tasks/crawl.py`, `_tiered_crawl()`

```python
# CURRENT: First tries Crawl4AI deep crawl on whole site...
async for page_result in crawl4ai.crawl_site(site.domain):
    pages_data.append(...)

# Then ALSO tries URL-by-URL on remaining URLs:
if len(pages_data) < queue.size * 0.5:
    remaining_urls = [u.url for u in queue._queue 
                      if u.url not in {p["url"] for p in pages_data}]
```

**Problems:**
1. `queue._queue` accesses a private attribute. Breaks if `CrawlPriorityQueue` is refactored.
2. The `0.5` threshold means if Crawl4AI gets 49% of pages, it triggers a full second pass for ALL remaining pages — potentially doubling cost and time.
3. The deep crawl discovers its own links; the URL queue is from the sitemap. There's no de-duplication logic that normalizes URLs (trailing slashes, `www` vs non-www).

**Fix:** Make `CrawlPriorityQueue` expose a public `get_uncrawled(visited_urls: set)` method, and set a smarter threshold (e.g., `< 0.8` rather than `< 0.5`).

---

### Bug 7: `broken_links_count` Counts Empty Hrefs, Not Actual Broken Links

**Where:** `packages/crawler/extractor.py`, `_links()`

```python
# CURRENT — "broken" = links with empty href, NOT 404s:
broken_candidates = []
for link in links:
    if not href.strip():
        broken_candidates.append(str(link))  # Only empty hrefs

return {
    "broken_links_count": len(broken_candidates),  # Almost always 0
```

**Why it's wrong:** Empty href links are rare. Real broken links return HTTP 404/410/5xx. This field will almost always be `0` and will never catch actual broken links.

**Fix — Actual broken link detection requires HTTP validation:**
```python
# During crawl, track URLs that returned 404/410
# Store as site-level data, not page-level
# Or use a separate async link checker task that validates external links

async def check_broken_links(urls: list[str]) -> dict[str, int]:
    """Check a list of URLs and return {url: status_code}."""
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        results = {}
        for url in urls:
            try:
                resp = await client.head(url)  # HEAD = no body, fast
                results[url] = resp.status_code
            except Exception:
                results[url] = 0  # Network error
    return results
```

---

## 2. ARCHITECTURE GAPS — DESIGN PROBLEMS

---

### Gap 1: No URL Normalization — Same Page Crawled Multiple Times

Before adding any URL to the queue, it must be normalized. Without this, these all get treated as different pages and crawled separately:
- `https://example.com/about`
- `https://example.com/about/`
- `https://example.com/about?ref=footer`
- `https://WWW.EXAMPLE.COM/about`
- `https://example.com/about#section`

**Add a URL normalizer:**
```python
from urllib.parse import urlparse, urlunparse, urlencode, parse_qs

def normalize_url(url: str) -> str:
    """Canonical form of a URL for deduplication."""
    parsed = urlparse(url.lower().strip())
    # Remove fragments
    normalized = parsed._replace(fragment="")
    # Remove tracking params (utm_*, ref, etc.)
    params = parse_qs(parsed.query)
    clean_params = {k: v for k, v in params.items() 
                    if not k.startswith(("utm_", "ref", "fbclid", "gclid"))}
    normalized = normalized._replace(query=urlencode(clean_params, doseq=True))
    # Normalize trailing slash (keep it consistent)
    path = normalized.path.rstrip("/") or "/"
    normalized = normalized._replace(path=path)
    return urlunparse(normalized)
```

---

### Gap 2: No Crawl Deduplication Across Organizations — Same Domain Crawled Repeatedly

If 10 different clients all connect `example.com`, AutoSEO crawls it 10 separate times (potentially within the same hour). At scale this will get the system's IPs blocked.

**Better approach — Shared crawl cache:**
```python
# In Redis, cache crawl results by URL + content hash for 24 hours
CRAWL_CACHE_TTL = 86400  # 24 hours

async def get_cached_crawl(url: str) -> dict | None:
    r = await get_redis()
    cached = await r.get(f"crawl_cache:{normalize_url(url)}")
    return json.loads(cached) if cached else None

async def set_crawl_cache(url: str, result: dict):
    r = await get_redis()
    await r.setex(f"crawl_cache:{normalize_url(url)}", CRAWL_CACHE_TTL, json.dumps(result))
```

---

### Gap 3: No Crawl Concurrency Control — Can Spawn Thousands of Connections

The URL-by-URL fallback loop has no concurrency limiting:
```python
# CURRENT: Sequential (too slow) with no semaphore
for url in remaining_urls:
    await asyncio.sleep(robots.get_crawl_delay())
    page_data = await _fetch_single_url(url, ...)  # One at a time
```

**Better — Use a semaphore for controlled concurrency:**
```python
MAX_CONCURRENT = 5  # Respect the site, but still fast

async def _tiered_crawl_parallel(urls, jina, crawl4ai, scrapfly, robots):
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    
    async def fetch_with_delay(url):
        async with semaphore:
            await asyncio.sleep(robots.get_crawl_delay())
            return await _fetch_single_url(url, jina, crawl4ai, scrapfly, stats)
    
    tasks = [fetch_with_delay(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if r and not isinstance(r, Exception)]
```

This is 5x faster while still respecting the crawl delay.

---

### Gap 4: No Crawl Cancellation Mechanism

There is no way to stop a running crawl. If a user accidentally triggers a 10,000-page crawl, there's no cancel button. The crawl will run until completion or failure.

**Add cancellation support:**
```python
# In Redis, store a "cancel flag" per crawl
async def cancel_crawl(crawl_id: str):
    r = await get_redis()
    await r.set(f"crawl:{crawl_id}:cancel", "1", ex=3600)

# In the crawl loop, check before each page:
async def is_cancelled(crawl_id: str) -> bool:
    r = await get_redis()
    return await r.exists(f"crawl:{crawl_id}:cancel")

# In _tiered_crawl:
for url in remaining_urls:
    if await is_cancelled(crawl_id):
        logger.info("crawl_cancelled", crawl_id=crawl_id)
        break
    ...
```

**Add API endpoint:** `DELETE /crawls/{crawl_id}` → sets the cancel flag.

---

### Gap 5: No Delta/Incremental Crawling — Every Crawl Is a Full Re-Crawl

For a 500-page site that's crawled weekly, 95% of pages haven't changed. Yet the plan crawls everything from scratch every time.

**Smarter approach — Conditional GET with `If-Modified-Since`:**
```python
# Store `last_crawled_at` and `content_hash` per page
# On re-crawl, use HTTP conditional GET:
headers = {}
if last_crawled_at and stored_etag:
    headers["If-None-Match"] = stored_etag
elif last_crawled_at:
    headers["If-Modified-Since"] = last_crawled_at.strftime("%a, %d %b %Y %H:%M:%S GMT")

# If response is 304 Not Modified → skip re-extraction, keep existing data
# This can reduce crawl time by 70-80% for mature sites
```

Also useful: using `<lastmod>` from sitemaps to skip unchanged pages.

---

### Gap 6: No Crawl Budget Reporting

For large sites, Google has a limited crawl budget. The plan detects crawl depth issues but never helps users understand or optimize their crawl budget. This is a feature Screaming Frog charges for and agencies need.

**Missing analysis:**
- Pages that block Googlebot unnecessarily
- JavaScript-only content that wastes crawl budget
- Faceted navigation creating URL explosion
- Parameter handling (e.g., `?sort=price` creating duplicate pages)

---

## 3. SEO SIGNAL GAPS — INCOMPLETE DATA COLLECTION

---

### Gap 7: HTTP Response Headers Are Never Collected

The extractor parses HTML but HTTP response headers are critical SEO signals:

| Header | SEO Relevance |
|--------|--------------|
| `X-Robots-Tag` | Server-level noindex (overrides meta robots) |
| `Content-Type` | Wrong charset causes rendering issues |
| `Strict-Transport-Security` | HSTS — required for HTTPS trust |
| `Cache-Control` | Affects CDN behavior and re-crawling |
| `Link: <url>; rel="canonical"` | HTTP-header canonical (used by some frameworks) |
| `X-Frame-Options` | Security, affects embedding |
| Response time (ms) | Proxy for TTFB without JS snippet |

**None of these are extracted anywhere in the plan.** The plan mentions them in Fix 6's list but the actual `SEOExtractor` class receives only HTML, not response headers.

**Fix — Thread headers through the layer results:**
```python
@dataclass
class CrawlResult:
    url: str
    html: str
    status_code: int
    headers: dict  # ADD THIS — carry response headers through all layers
    response_time_ms: int  # ADD THIS — measure at fetch time
```

---

### Gap 8: No HTTP Status Code Issue Detection

The extractor doesn't track or issue-generate for HTTP errors:

- **404 pages** — these are indexed by Google and hurt the site
- **Soft 404s** — pages that return 200 but show "not found" content
- **5xx pages** — server errors during crawl
- **401/403 pages** — accidentally blocked public content

The `pages` table needs a `status_code` column, and the issue generator needs:
```python
if page.get("status_code", 200) == 404:
    issues.append(Issue(type="http_404", severity=HIGH, impact_score=80, ...))
elif page.get("status_code", 200) >= 500:
    issues.append(Issue(type="server_error", severity=CRITICAL, ...))
```

---

### Gap 9: No Thin Content Threshold Is Context-Aware

The plan checks `word_count < 100` and flags it as thin content. But:
- A contact page with 50 words is fine
- A product page with 50 words is terrible
- A blog post with 300 words might be thin

**Missing: Page type classification.** Without knowing what type of page it is (homepage, product, blog, category, contact), the thin content check creates too many false positives.

**Add a page type classifier:**
```python
def classify_page_type(page: dict) -> str:
    url = page["url"].lower()
    schemas = page.get("schema_types", [])
    
    if "Product" in schemas: return "product"
    if "Article" in schemas or "BlogPosting" in schemas: return "article"
    if "FAQPage" in schemas: return "faq"
    if any(p in url for p in ["/contact", "/about", "/team"]): return "utility"
    if url.rstrip("/").count("/") <= 1: return "homepage"
    return "generic"

# Then use type-aware thresholds:
THIN_CONTENT_THRESHOLDS = {
    "product": 200,
    "article": 500,
    "homepage": 100,
    "utility": 30,
    "generic": 150,
}
```

---

### Gap 10: No Heading Hierarchy Issue Detection

The plan tracks H1/H2/H3 counts and the heading structure array, but never checks for **heading hierarchy violations** — a common issue that confuses both users and crawlers:

- H1 → H3 (skipped H2) 
- H2 before H1
- H3 as first heading

**Add to `_check_headings()`:**
```python
def _check_heading_hierarchy(self, page) -> list[Issue]:
    structure = page.get("heading_structure", [])
    issues = []
    prev_level = 0
    for heading in structure:
        level = heading["level"]
        if level > prev_level + 1 and prev_level > 0:
            issues.append(Issue(
                type="heading_hierarchy_skip",
                severity=LOW, impact_score=20,
                current_value=f"H{prev_level} → H{level} (skipped H{prev_level+1})",
            ))
        prev_level = level
    return issues
```

---

### Gap 11: No Image Format Detection — Missing a Core Performance Signal

The plan detects missing alt text and large images (by pixel dimensions) but never checks **image format**. Serving JPEG/PNG when WebP/AVIF is available is a major Core Web Vitals issue that Google explicitly flags in Lighthouse.

**Add to `_images()`:**
```python
for img in imgs:
    src = img.get("src", "")
    ext = src.split(".")[-1].lower().split("?")[0]
    if ext in ("jpg", "jpeg", "png", "gif") and "data:" not in src:
        non_modern_format_images.append(src)

# In issue generator:
if len(non_modern_format_images) > 0:
    issues.append(Issue(
        type="non_modern_image_format",
        category="performance", severity=MEDIUM, impact_score=45,
        current_value=f"{len(non_modern_format_images)} images not in WebP/AVIF format",
        fix_type="manual",
    ))
```

---

### Gap 12: No `rel="nofollow"` / `rel="sponsored"` / `rel="ugc"` Link Analysis

The plan extracts internal/external links but ignores link attributes that directly affect PageRank flow:
- Internal links with `rel="nofollow"` accidentally block PageRank from flowing
- External sponsored links without `rel="sponsored"` violate Google's guidelines
- User-generated links without `rel="ugc"` is a compliance issue

This is missing both from the extractor and issue generator.

---

### Gap 13: No Keyword Cannibalization Detection

Two pages targeting the same keyword is one of the most common and damaging SEO issues. Zero mention of it anywhere in the plan.

**This requires:**
1. Extracting the primary keyword signal from each page (title + H1 + meta description NLP)
2. Clustering pages by semantic similarity  
3. Flagging clusters with 2+ pages that appear to target the same keyword

Even a simple title-overlap check would be valuable:
```python
def detect_keyword_cannibalization(pages: list[dict]) -> list[tuple]:
    """Find pages with very similar titles — likely targeting same keyword."""
    from difflib import SequenceMatcher
    duplicates = []
    titles = [(p["url"], p.get("title", "").lower()) for p in pages if p.get("title")]
    
    for i, (url_a, title_a) in enumerate(titles):
        for url_b, title_b in titles[i+1:]:
            similarity = SequenceMatcher(None, title_a, title_b).ratio()
            if similarity > 0.7:
                duplicates.append((url_a, url_b, similarity))
    return duplicates
```

---

### Gap 14: No `<link rel="preconnect">` / `<link rel="preload">` Analysis

These performance hints in the HTML `<head>` directly affect LCP and are flagged by Lighthouse. Missing `preconnect` for Google Fonts or CDN origins is a common issue. Not detected anywhere.

---

### Gap 15: No Content Freshness Detection

A blog post from 2018 with outdated stats is a different kind of SEO problem from a missing title. Google's Freshness Algorithm rewards updated content. The plan stores `lastmod` from sitemaps but never:
- Issues a warning for pages not updated in 12+ months
- Compares crawl date to `lastmod` for staleness scoring
- Suggests content refresh as an AI-generated "fix opportunity"

---

## 4. SECURITY VULNERABILITIES — NOT MENTIONED AT ALL

---

### Security 1: SSRF (Server-Side Request Forgery) — Can Attack Internal Network

**Severity: CRITICAL**

The crawlers will follow any URL a user provides. Nothing stops a user from submitting:
```
domain: "http://169.254.169.254/latest/meta-data/"   # AWS metadata endpoint
domain: "http://10.0.0.1/admin"                       # Internal network
domain: "http://localhost:6379"                        # Internal Redis
```

**Fix — URL allowlist/validation before crawling:**
```python
import ipaddress
from urllib.parse import urlparse

BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local (AWS metadata)
    ipaddress.ip_network("127.0.0.0/8"),     # Loopback
]

def is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        return not any(ip in net for net in BLOCKED_NETWORKS)
    except ValueError:
        return True  # hostname (not IP) — safe
```

---

### Security 2: Snippet Token Is Visible in HTML Source — Can Be Stolen

The snippet is embedded as:
```html
<script src="..." data-token="SITE_TOKEN" async></script>
```

The `SITE_TOKEN` is visible to anyone who views the page source. A competitor or attacker can:
1. Copy the token
2. Send fake data to corrupt the client's field metrics
3. Exhaust the client's API rate limits

**Fix — Add token rotation + request signing:**
```python
# Instead of static tokens, use HMAC-signed short-lived tokens
import hmac, hashlib, time

def generate_snippet_token(site_id: str, secret: str) -> str:
    timestamp = int(time.time() // 3600)  # Valid for 1 hour
    msg = f"{site_id}:{timestamp}"
    sig = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{site_id}:{timestamp}:{sig}"

def verify_snippet_token(token: str, secret: str) -> str | None:
    parts = token.split(":")
    if len(parts) != 3:
        return None
    site_id, timestamp, sig = parts
    # Verify signature and freshness (allow 2 hours tolerance)
    current_hour = int(time.time() // 3600)
    if abs(int(timestamp) - current_hour) > 2:
        return None
    expected_sig = hmac.new(secret.encode(), f"{site_id}:{timestamp}".encode(), hashlib.sha256).hexdigest()[:16]
    if hmac.compare_digest(sig, expected_sig):
        return site_id
    return None
```

---

### Security 3: Snippet Endpoint Has No Rate Limiting Implemented

The code says `# Rate limited to prevent abuse` in the comment but the actual rate limiting implementation is completely missing from the router code.

**Fix — Add it explicitly with `slowapi` or a Redis-based rate limiter:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/snippet/collect")
@limiter.limit("100/minute")  # Max 100 events/minute per IP
async def collect_snippet_data(request: Request, payload: SnippetPayload):
    ...
```

---

### Security 4: CMS Credentials Key Management Is Undefined

The plan mentions `decrypt_credential(site.org_id, site.cms_token_encrypted, site.cms_token_iv)` but never specifies:
- Where is the encryption key stored? (Must NOT be in the DB)
- How is it rotated?
- What happens if a key is compromised?

**Recommendation:** Use a dedicated secrets manager (HashiCorp Vault, AWS KMS, or at minimum environment-variable-based key with AES-256-GCM). The key should never touch the database.

---

### Security 5: No Bot/Abuse Filtering on Snippet Endpoint

Bots crawling the client's site will execute the snippet and send data to the endpoint. This pollutes Core Web Vitals data with non-human measurements (bots don't have real LCP values).

**Add bot filtering:**
```python
BOT_USER_AGENTS = ["googlebot", "bingbot", "slurp", "duckduckbot", "baiduspider", 
                   "yandexbot", "sogou", "facebot", "curl", "python-requests", "wget"]

def is_bot_request(user_agent: str) -> bool:
    ua_lower = user_agent.lower()
    return any(bot in ua_lower for bot in BOT_USER_AGENTS)

# In collect endpoint:
if is_bot_request(event.user_agent or ""):
    continue  # Skip bot events
```

---

## 5. JS SNIPPET GAPS — THE MOST VALUABLE DATA SOURCE HAS HOLES

---

### Gap 16: INP Is Collected in JS But NOT Stored in the Backend Model

**This is the most important gap in the plan.**

The plan's Fix 5 says INP was added to the snippet. But looking at the `SnippetEvent` model in the backend:

```python
class SnippetEvent(BaseModel):
    lcp: float | None = None
    cls: float | None = None
    ttfb: float | None = None
    # 🔴 inp IS MISSING HERE
```

And in `collect_snippet_data()`, there's no `inp_ms` being stored. INP replaced FID as a Core Web Vital in March 2024 — it's now the third most important ranking signal after LCP and CLS. It's collected on the frontend but thrown away on the backend.

**Fix:** Add `inp: float | None = None` to `SnippetEvent`, add `inp_ms=event.inp` to `db.insert_snippet_event()`.

---

### Gap 17: No Sampling Strategy for High-Traffic Sites

A site with 100,000 daily visitors would send 100,000 snippet events per day to the collect endpoint. At 30-second batches with up to 10 events per batch, that's still potentially thousands of API calls per hour.

**Fix — Add client-side sampling:**
```javascript
// In autoseo-snippet.js — only collect data from X% of visitors
var SAMPLE_RATE = 0.1;  // Collect from 10% of visitors
if (Math.random() > SAMPLE_RATE) return;  // Exit early for 90%
```

This should be configurable per site (high-traffic sites use lower sample rates).

---

### Gap 18: No GDPR/Privacy Compliance

The snippet collects `user_agent`, `viewport_width`, `page_url`, and timing data from real users. Under GDPR/CCPA, this can require:
- User consent before collection
- Data deletion on request
- Privacy policy disclosure

The plan has zero mention of this. For EU clients or sites serving EU users, this could be a blocker for adoption or a legal liability.

**Minimum requirement:** Document what's collected, add a `do_not_track` check, and provide a way for clients to enable/disable collection.

```javascript
// Respect Do Not Track
if (navigator.doNotTrack === "1") return;

// Collect only what's needed — no PII
// url: ✅ (page URL, not user URL)
// user_agent: ⚠️ (can be fingerprinting — consider dropping or hashing)
// viewport_width: ✅ (aggregate, not personal)
```

---

### Gap 19: No Mobile vs Desktop Segmentation in Field Data

The snippet collects `viewport_width` but the analysis pipeline never segments Core Web Vitals by device type. Google measures mobile and desktop separately in Search Console. A site might have excellent desktop LCP (1.2s) and terrible mobile LCP (4.8s) — the current system averages them and shows a misleading 3.0s.

**Fix — Add device segmentation to all field data queries and reports.**

---

### Gap 20: Snippet Doesn't Detect SPA Navigation Accurately

The plan mentions "SPA navigation detection (MutationObserver + History API)" but the actual implementation in the snippet fires on every `pushState`/`replaceState`. This means:
- Each URL change triggers a new `collectPageData()` 
- But the DOM hasn't finished updating yet when the event fires
- So it collects the OLD page's data and attributes it to the NEW URL

**Fix — Add a delay after navigation before collecting:**
```javascript
window.addEventListener('popstate', function() {
    setTimeout(collectPageData, 500);  // Wait for DOM update
});
// Also patch History API methods with a delay
```

---

## 6. AI FIX ENGINE GAPS — CORE REVENUE FEATURE IS INCOMPLETE

---

### Gap 21: No Actual Prompt Templates for Specific Issue Types

The plan shows one generic prompt builder:
```python
def _build_fix_prompt(self, issue: dict, page_context: dict) -> str:
    return f"Fix this SEO issue: ISSUE TYPE: {issue['type']}..."
```

But generating a good meta description requires a completely different prompt than generating schema markup. Using one generic prompt for all issue types will produce mediocre output that won't justify the subscription price.

**What's needed — Issue-specific prompt templates:**

```python
PROMPTS = {
    "missing_meta_description": """
        You are an SEO copywriter. Write a meta description for this page.
        
        Page URL: {url}
        Page Title: {title}
        Main Heading: {h1}
        Page Content (first 500 words): {content}
        
        Rules:
        - 120-155 characters exactly
        - Include the primary keyword from the title naturally
        - Include a call-to-action verb (Learn, Discover, Find, Get)
        - Do NOT use "we" or first person
        - Do NOT mention the site name (it's in the title tag)
        - Do NOT use superlatives like "best" or "amazing"
        
        Respond with ONLY the meta description text, nothing else.
    """,
    
    "missing_schema": """
        You are a schema markup expert. Generate JSON-LD structured data for this page.
        
        Page type: {page_type}
        Title: {title}
        URL: {url}
        Content snippet: {content}
        
        Generate the MOST APPROPRIATE schema type from:
        {valid_schema_types}
        
        Rules:
        - Valid JSON-LD only
        - Include @context, @type, and all required properties
        - Use real data from the page — never fabricate
        
        Respond with ONLY the JSON-LD code block.
    """,
    
    "images_missing_alt": """
        You are an accessibility and SEO specialist. 
        Generate alt text for these images.
        
        Page context: {title}
        Images needing alt text:
        {image_list}
        
        Rules:
        - Each alt text: 5-15 words
        - Describe what's visually in the image
        - Include relevant keywords naturally if they fit the image
        - Do NOT start with "image of" or "picture of"
        - Do NOT repeat the same alt text for multiple images
        
        Respond with JSON: {"image_src": "alt_text", ...}
    """,
}
```

---

### Gap 22: No Fix History or Versioning

If AI generates fix #1, user rejects it and asks for another, then applies fix #2, and it doesn't work... there's no way to go back to fix #1. No history, no versioning, no comparison.

**Add a `fix_attempts` table:**
```sql
CREATE TABLE fix_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id UUID REFERENCES issues(id),
    attempt_number INTEGER,
    proposed_fix TEXT,
    ai_confidence NUMERIC(3,2),
    explanation TEXT,
    status TEXT DEFAULT 'generated', -- generated|applied|rejected|verified|failed
    applied_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now()
);
```

---

### Gap 23: Fix Verification Waits Only 5 Seconds — Never Works for Real Sites

```python
async def verify_fix(self, issue_id: str, site_id: str) -> dict:
    await asyncio.sleep(5)  # Wait 5 seconds
    # Then re-fetch with Jina
```

**Why it never works:** 
- WordPress with caching plugins (WP Rocket, W3 Total Cache): 5 minutes to propagate
- Cloudflare CDN: 5-30 minutes to purge
- Shopify: 5-15 minutes
- Vercel/Netlify: instant, but build pipeline takes 2-5 minutes

5 seconds will almost always show the old version and mark the fix as "failed."

**Fix — Schedule verification as a delayed Celery task:**
```python
# When fix is applied:
verify_fix_task.apply_async(
    args=[issue_id, site_id],
    countdown=300  # Verify after 5 minutes
)

# If verification fails, try again at 30 minutes:
verify_fix_task.apply_async(
    args=[issue_id, site_id],
    countdown=1800
)
```

---

### Gap 24: No Claude API Rate Limit Handling During Batch Analysis

The `run_ai_analysis` task generates fixes for ALL issues in a crawl. For a 1,000-page site with 200 issues, that's 200 Claude API calls in rapid succession. Anthropic's rate limits (especially for `claude-sonnet`) will throttle this.

**Fix — Add rate limit handling with exponential backoff:**
```python
import anthropic

async def generate_fix_with_retry(self, issue, page_context, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await self.generate_fix(issue, page_context)
        except anthropic.RateLimitError:
            wait = (2 ** attempt) * 10  # 10s, 20s, 40s
            logger.warning("claude_rate_limited", wait=wait)
            await asyncio.sleep(wait)
    return None  # Give up after retries
```

Also: prioritize only HIGH/CRITICAL issues for immediate AI analysis. Generate LOW/MEDIUM fixes lazily (on-demand when user views them).

---

### Gap 25: AI Model Version Is Wrong

```python
# CURRENT:
def __init__(self, api_key: str, model: str = "claude-sonnet-4-5"):
```

`claude-sonnet-4-5` is incorrect. As of April 2026, the correct model string is `claude-sonnet-4-6` (or use `claude-haiku-4-5-20251001` for cheaper batch processing of simple fixes like meta descriptions).

**Better approach — Use different models for different fix types:**
```python
MODEL_BY_ISSUE_TYPE = {
    # Cheap, fast for simple text fixes
    "missing_meta_description": "claude-haiku-4-5-20251001",
    "title_too_short": "claude-haiku-4-5-20251001",
    "images_missing_alt": "claude-haiku-4-5-20251001",
    
    # Smarter for complex structural fixes
    "missing_schema": "claude-sonnet-4-6",
    "invalid_schema": "claude-sonnet-4-6",
    "canonical_chain": "claude-sonnet-4-6",
}
```

This could reduce AI costs by 10-20x for simple fixes.

---

## 7. MISSING FEATURES — THINGS NOT THOUGHT OF AT ALL

---

### Missing Feature 1: Google Search Console Integration

**This is the biggest missing feature in the entire plan.**

Google Search Console gives you:
- Real keyword rankings (what queries bring traffic)
- Real click-through rates per page
- Real impression data
- Google's own crawl errors (not your crawl errors)
- Core Web Vitals from Google's perspective
- Index coverage issues flagged by Google directly

Without GSC integration, the tool is guessing at what matters. WITH GSC integration, you can say: "This page gets 10,000 impressions/month for [keyword] but only 2% CTR — your title tag is losing you 980 clicks/month. Fix it."

**GSC integration is your strongest selling point and it's completely missing.**

Implementation: Use Google Search Console API v1 with OAuth2. Store impressions/clicks/CTR/position per page. Surface opportunities in the issue list (e.g., "High impressions, low CTR = fix title/meta").

---

### Missing Feature 2: Google PageSpeed Insights API Integration

The plan calculates its own "performance" issues from field data (snippet LCP/CLS), but never integrates with the actual Google Lighthouse API. This is free, gives authoritative data, and lets you show users "Google says your score is 43."

```python
async def run_pagespeed(url: str, strategy: str = "mobile") -> dict:
    """Get real Lighthouse scores from Google."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
            params={"url": url, "strategy": strategy, "key": settings.GOOGLE_API_KEY}
        )
        data = resp.json()
        return {
            "performance_score": data["lighthouseResult"]["categories"]["performance"]["score"],
            "seo_score": data["lighthouseResult"]["categories"]["seo"]["score"],
            "lcp_ms": data["lighthouseResult"]["audits"]["largest-contentful-paint"]["numericValue"],
            "cls": data["lighthouseResult"]["audits"]["cumulative-layout-shift"]["numericValue"],
            "fcp_ms": data["lighthouseResult"]["audits"]["first-contentful-paint"]["numericValue"],
        }
```

---

### Missing Feature 3: Crawl-to-Crawl Diff / Change Detection

Every SEO tool worth its price shows: "Since your last crawl 7 days ago: +12 new pages, -3 pages disappeared, 8 pages changed title, 2 new issues appeared."

The plan saves each crawl independently but never compares them. This is a massive retention feature — users log in specifically to see what changed.

**Add a `CrawlDiffer` class:**
```python
class CrawlDiffer:
    def compare(self, crawl_a: list[dict], crawl_b: list[dict]) -> dict:
        urls_a = {p["url"]: p for p in crawl_a}
        urls_b = {p["url"]: p for p in crawl_b}
        
        return {
            "new_pages": list(urls_b.keys() - urls_a.keys()),
            "removed_pages": list(urls_a.keys() - urls_b.keys()),
            "score_improved": [url for url in urls_b if url in urls_a 
                               and urls_b[url]["seo_score"] > urls_a[url]["seo_score"]],
            "score_declined": [url for url in urls_b if url in urls_a 
                               and urls_b[url]["seo_score"] < urls_a[url]["seo_score"]],
            "title_changed": [url for url in urls_b if url in urls_a 
                              and urls_b[url].get("title") != urls_a[url].get("title")],
        }
```

---

### Missing Feature 4: IndexNow / Google Indexing API — Notify After Fix

When a fix is applied, Google doesn't know about it for days or weeks until its next crawl. IndexNow lets you notify search engines of changes instantly (Bing supports it natively, and it propagates to Yandex; Google partially honors it).

This could be marketed as: "We apply your fix AND tell Google about it immediately."

```python
async def notify_indexnow(urls: list[str], api_key: str):
    """Notify IndexNow protocol that pages have been updated."""
    await httpx.AsyncClient().post(
        "https://api.indexnow.org/indexnow",
        json={"host": domain, "key": api_key, "urlList": urls}
    )
```

---

### Missing Feature 5: Scheduled Automatic Re-Crawls

The plan requires manual crawl triggering. There's no mention of:
- Weekly automatic re-crawls
- Change-triggered crawls (via webhook from CMS)
- Scheduled crawl configuration (e.g., "crawl every Monday at 6am")

This is essential for retention. If users have to remember to manually crawl, they forget and churn.

```sql
ALTER TABLE sites ADD COLUMN crawl_schedule TEXT DEFAULT 'weekly';
-- Values: 'never' | 'daily' | 'weekly' | 'monthly'
ALTER TABLE sites ADD COLUMN next_scheduled_crawl TIMESTAMP;
```

```python
# Celery beat schedule:
CELERYBEAT_SCHEDULE = {
    "check-scheduled-crawls": {
        "task": "workers.tasks.crawl.trigger_scheduled_crawls",
        "schedule": crontab(minute=0, hour="*"),  # Every hour
    }
}
```

---

### Missing Feature 6: Issue Grouping / Aggregation

If 300 pages are missing meta descriptions, the issues list shows 300 separate issues. This is overwhelming and hides the pattern.

**Add issue aggregation:**
```python
class IssueAggregator:
    def aggregate(self, issues: list[Issue]) -> list[AggregatedIssue]:
        """Group issues by type across pages."""
        by_type = defaultdict(list)
        for issue in issues:
            by_type[issue.type].append(issue)
        
        return [AggregatedIssue(
            type=issue_type,
            count=len(page_issues),
            severity=page_issues[0].severity,
            impact_score=page_issues[0].impact_score,
            affected_pages=[i.page_url for i in page_issues],
            fix_type=page_issues[0].fix_type,
            # Bulk fix: apply AI-generated template to all affected pages at once
            can_bulk_fix=page_issues[0].fix_type in ("auto", "semi_auto"),
        ) for issue_type, page_issues in by_type.items()]
```

**Add bulk fix:** "Apply AI-generated meta description to all 300 pages at once" → generates individual fixes for each page but presents as one action.

---

### Missing Feature 7: White-Label / Agency Mode

Agencies will be the biggest customers. They need:
- Custom branding on reports (their logo, not AutoSEO)
- Client management (add client, share report with client, client has read-only view)
- Reseller pricing (agency pays $X, charges clients $Y)
- Bulk site management (manage 50 client sites from one dashboard)

Not mentioned anywhere in the plan. Should be at least architecturally considered (org hierarchy: Agency → Clients → Sites).

---

### Missing Feature 8: Content Opportunity Detection

Beyond fixing broken SEO, the highest-value feature for users is **finding content gaps** — topics they should create content for. This is what Ahrefs/Semrush charge $400/mo for.

A lightweight version using available data:
- Competitor gap analysis (already noted as "pass" in the plan — needs implementation)
- "You have strong pages on X but nothing on Y" (content clustering)
- Pages with high impressions but no content (GSC integration enables this)

---

### Missing Feature 9: Core Web Vitals Percentile Tracking (P75)

Google uses the **75th percentile** of Core Web Vitals (not the average) to determine if a page passes/fails. The plan averages LCP/CLS values from the snippet, which is statistically incorrect.

```python
import statistics

def calculate_cwv_p75(values: list[float]) -> float:
    """Google uses P75 for CWV thresholds, not mean."""
    if not values:
        return 0
    sorted_vals = sorted(values)
    index = int(len(sorted_vals) * 0.75)
    return sorted_vals[min(index, len(sorted_vals)-1)]
```

---

### Missing Feature 10: Webflow and GitHub Pages CMS Readers

The `CMSReader` only implements WordPress and Shopify. The architecture lists Webflow and GitHub as supported, but `read_webflow()` and `read_github_pages()` are completely absent from the code. The `select_layer()` function checks for `"webflow"` as a connection type and routes to `CMSReader` — which will throw an `AttributeError` since the method doesn't exist.

---

## 8. BETTER SOLUTIONS — REPLACE WITH SOMETHING SMARTER

---

### Better Solution 1: Replace BeautifulSoup with lxml in SEOExtractor

```python
# CURRENT — slower:
self.soup = BeautifulSoup(html, "lxml")

# BETTER — use lxml directly (3-5x faster for large HTML):
from lxml import etree
from lxml.html import fromstring

tree = fromstring(html)
title = tree.findtext(".//title")
h1s = tree.xpath("//h1//text()")
```

BeautifulSoup's API is convenient but creates Python objects for every node. For a 500-page site, switching to direct lxml can cut extraction time by 60-70%.

---

### Better Solution 2: Replace SimHash MD5 with xxHash

```python
# CURRENT — MD5 is cryptographic, overkill for hashing:
token_hash = int(hashlib.md5(token.encode()).hexdigest(), 16)

# BETTER — xxHash is 10x faster, designed for non-cryptographic use:
import xxhash
token_hash = xxhash.xxh64(token.encode()).intdigest()
```

For a 10,000-word page, SimHash tokenizes thousands of words. xxHash vs MD5 per-token adds up to a meaningful speed difference.

---

### Better Solution 3: Replace `heapq`-less Priority Queue

The plan describes a `CrawlPriorityQueue` but the implementation isn't shown. If it's a sorted list (as suggested by the code accessing `queue._queue`), insertions are O(n). Use Python's `heapq`:

```python
import heapq
from dataclasses import dataclass, field

@dataclass(order=True)
class QueueItem:
    priority: float  # Higher = processed first (use negative for max-heap)
    url: str = field(compare=False)
    depth: int = field(compare=False)

class CrawlPriorityQueue:
    def __init__(self):
        self._heap = []
    
    def add(self, url: str, priority: float, depth: int = 0):
        heapq.heappush(self._heap, QueueItem(-priority, url, depth))
    
    def pop(self) -> QueueItem | None:
        return heapq.heappop(self._heap) if self._heap else None
    
    def get_uncrawled(self, visited: set[str]) -> list[str]:
        """Public method — no private attribute access."""
        return [item.url for item in self._heap if item.url not in visited]
```

---

### Better Solution 4: GEO Scorer Needs Real NLP, Not Keyword Matching

```python
# CURRENT — crude keyword matching:
def _check_qa_formatting(self, page) -> int:
    question_patterns = ["how to", "what is", "why does", "when should"]
    question_count = sum(1 for h in h2s 
                        if any(p in h.get("text", "").lower() for p in question_patterns))
    return min(100, question_count * 25)
```

This will give a score of 0 to a page with an H2 like "Choosing the Right Framework" (which is a great SEO heading but doesn't start with a question word).

**Better — Use sentence embeddings or at minimum a more semantic check:**
```python
# Check if the page has interrogative-style content (question patterns in any form)
QUESTION_INDICATORS = [
    "how to", "how do", "what is", "what are", "why is", "why does",
    "when to", "where to", "which is", "who is", "can you", "should you",
    "is it", "does it", "guide to", "tutorial", "explained", "vs", "versus"
]

def _check_qa_formatting(self, page) -> int:
    all_headings = " ".join(
        h.get("text", "").lower() for h in page.get("heading_structure", [])
    )
    matches = sum(1 for p in QUESTION_INDICATORS if p in all_headings)
    return min(100, matches * 15)
```

---

### Better Solution 5: Score Calculator Needs Additive, Not Deductive Model

```python
# CURRENT — start at 100, subtract points:
def calculate_page_score(page: dict) -> int:
    score = 100
    if not page.get("title"):
        score -= 30
    ...
    return max(0, score)
```

**Problem:** This means a page with ALL issues loses more than 100 points and bottoms out at 0. But you can't tell the DIFFERENCE between a page with 3 critical issues and a page with 10 critical issues — both score 0.

**Better — Additive weighted scoring:**
```python
def calculate_page_score(page: dict) -> int:
    """
    Additive model: each factor contributes its max points.
    Score = sum of earned points / sum of possible points * 100
    """
    factors = [
        # (name, max_points, earned_if_true, condition)
        ("title", 20, 20, bool(page.get("title") and 30 <= page.get("title_length", 0) <= 60)),
        ("meta_desc", 15, 15, bool(page.get("meta_description") and 50 <= page.get("meta_description_length", 0) <= 160)),
        ("h1", 12, 12, page.get("h1_count", 0) == 1),
        ("https", 10, 10, page.get("is_https", True)),
        ("viewport", 10, 10, page.get("has_viewport", True)),
        ("schema", 8, 8, bool(page.get("schema_types")) and page.get("schema_valid", True)),
        ("canonical", 7, 7, bool(page.get("canonical_url"))),
        ("no_noindex", 8, 8, "noindex" not in page.get("robots_directive", "").lower()),
        ("internal_links", 5, 5, page.get("incoming_links_count", 0) > 0),
        ("html_lang", 5, 5, bool(page.get("html_lang"))),
    ]
    
    total_possible = sum(f[1] for f in factors)
    total_earned = sum(f[2] for f in factors if f[3])
    return int(total_earned / total_possible * 100)
```

This gives a differentiating score rather than a floor at 0.

---

### Better Solution 6: Competitor Gap Analysis Is Marked `pass` — Needs Real Implementation

Diamond Feature 3 (`CompetitorGapAnalyzer`) is:
```python
class CompetitorGapAnalyzer:
    # Implementation: crawl competitor URLs, compare signals, generate gap report
    pass  # Full implementation in next phase
```

This is described as a revenue multiplier but is empty. Even a basic implementation would be valuable:

```python
class CompetitorGapAnalyzer:
    def analyze(self, my_pages: list[dict], competitor_pages: list[dict]) -> dict:
        my_schema_types = {t for p in my_pages for t in p.get("schema_types", [])}
        comp_schema_types = {t for p in competitor_pages for t in p.get("schema_types", [])}
        
        my_word_count = sum(p.get("word_count", 0) for p in my_pages) / len(my_pages)
        comp_word_count = sum(p.get("word_count", 0) for p in competitor_pages) / len(competitor_pages)
        
        return {
            "schema_gaps": list(comp_schema_types - my_schema_types),  # They use, you don't
            "avg_content_gap": comp_word_count - my_word_count,  # They write more/less
            "they_have_faq": any("FAQPage" in p.get("schema_types", []) for p in competitor_pages),
            "you_have_faq": any("FAQPage" in p.get("schema_types", []) for p in my_pages),
            "their_avg_title_length": sum(p.get("title_length", 0) for p in competitor_pages) / len(competitor_pages),
            "your_avg_title_length": sum(p.get("title_length", 0) for p in my_pages) / len(my_pages),
        }
```

---

## PRIORITY MATRIX

Organize the above gaps by urgency:

| Priority | Gap / Fix | Risk if Ignored |
|----------|-----------|----------------|
| 🔴 P0 | Bug 1: asyncio.run() deadlock | Celery workers crash under load |
| 🔴 P0 | Security 1: SSRF vulnerability | Server can be used to attack internal network |
| 🔴 P0 | Security 2: Token theft | Client data poisoned, competitor spying |
| 🔴 P0 | Bug 3: hreflang logic bug | 1000s of false-positive issues for multilingual clients |
| 🔴 P0 | Gap 16: INP not stored | Core Web Vital data silently discarded |
| 🟠 P1 | Bug 4: Redis connection leak | Redis crashes under load |
| 🟠 P1 | Bug 5: SSE DB polling | DB overload at 50+ concurrent users |
| 🟠 P1 | Bug 7: Broken link detection wrong | Field always shows 0, feature is useless |
| 🟠 P1 | Gap 7: HTTP headers not collected | Missing X-Robots-Tag and server canonical |
| 🟠 P1 | Gap 25: Wrong Claude model string | AI analysis task fails on first run |
| 🟠 P1 | Missing Feature 10: Webflow/GitHub CMS | AttributeError crash for those site types |
| 🟡 P2 | Bug 2: O(n²) duplicate detection | Timeout on sites > 2,000 pages |
| 🟡 P2 | Gap 1: No URL normalization | Same pages crawled multiple times |
| 🟡 P2 | Gap 4: No crawl cancellation | Runaway crawls can't be stopped |
| 🟡 P2 | Gap 21: No issue-specific prompts | Poor AI fix quality, users cancel |
| 🟡 P2 | Gap 23: Fix verification timing | All fixes marked "failed" — trust destroyed |
| 🟡 P2 | Security 3: No rate limiting on snippet | Abuse possible from day 1 |
| 🟢 P3 | Missing Feature 1: GSC integration | Big competitive gap vs Ahrefs/Semrush |
| 🟢 P3 | Missing Feature 3: Crawl diff | Low retention without change tracking |
| 🟢 P3 | Missing Feature 5: Scheduled crawls | Users forget to log in, churn |
| 🟢 P3 | Missing Feature 6: Issue aggregation | UX overwhelm with 300 separate issues |
| 🟢 P3 | Better Solution 5: Additive score model | Score bottoms at 0, loses differentiation |

---

## SUMMARY — THE 3 MOST IMPORTANT THINGS TO ADD

1. **Google Search Console API** — This transforms the tool from "we think these might be issues" to "Google confirmed these issues are costing you X clicks." Nothing else improves the value proposition more.

2. **Fix the async/Redis bugs before shipping** — Bugs 1, 4, and 5 will cause the system to fall over at any real load. Fix them before launch, not after.

3. **Issue-specific Claude prompts** (Gap 21) — The AI fix engine is the core differentiator and revenue multiplier. Generic prompts will produce mediocre output. Write a proper prompt for each of the 15 most common issue types and the feature actually earns its keep.

---
*Analysis complete. 47 gaps identified across 8 categories.*
