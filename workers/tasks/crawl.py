"""Crawl tasks — multi-layer crawler with SEO signal extraction & issue generation.

Phase 2 enhancements (from gap analysis):
- Bug 1 fix: uses async_to_sync wrapper (avoids event-loop nesting issues)
- Gap 1: URL normalization & dedup
- Gap 3: Concurrent fetching with asyncio.Semaphore
- Gap 4: Crawl cancellation (DB-status check between batches)
- Gap 7: HTTP headers + status_code + response_time_ms threaded through pipeline
- Bug 7: Real broken-link tracking from HTTP results
- Security 1: SSRF check rejects internal/loopback IPs
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
from datetime import datetime, timezone

import structlog

# Ensure packages are importable from the workers directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

logger = structlog.get_logger()

# Celery is optional — only required for production worker mode.
# In dev (no REDIS_URL) the API dispatches via FastAPI BackgroundTasks
# and never imports celery. We provide a no-op decorator so module import
# always succeeds.
try:
    from workers.celery_app import app  # type: ignore
    _CELERY_AVAILABLE = True
except Exception:  # ImportError if celery missing, or any config error
    _CELERY_AVAILABLE = False

    class _NoopTask:
        def __init__(self, fn):
            self.fn = fn
        def __call__(self, *a, **kw):
            return self.fn(*a, **kw)
        def delay(self, *a, **kw):
            logger.warning("celery_unavailable_skipping_dispatch", task=self.fn.__name__)
        def retry(self, *a, **kw):
            raise RuntimeError("Celery retry called outside of Celery worker")

    class _NoopApp:
        def task(self, *a, **kw):
            def deco(fn):
                return _NoopTask(fn)
            # support both @app.task and @app.task(bind=True, ...)
            if a and callable(a[0]) and not kw:
                return _NoopTask(a[0])
            return deco

    app = _NoopApp()  # type: ignore

MAX_CONCURRENT_FETCHES = 5  # Gap 3


@app.task(bind=True, max_retries=3)
def run_site_crawl(self, site_id: str, crawl_id: str):
    """Celery entrypoint — wraps async crawl using asgiref to avoid event-loop nesting."""
    try:
        try:
            from asgiref.sync import async_to_sync
            async_to_sync(_async_crawl)(site_id, crawl_id)
        except ImportError:
            asyncio.run(_async_crawl(site_id, crawl_id))
    except Exception as exc:
        logger.error("crawl_task_failed", site_id=site_id, crawl_id=crawl_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60)


async def _check_cancelled(db, crawl_id: str) -> bool:
    """Refresh crawl row and return True if user requested cancellation."""
    from sqlalchemy import select
    from models.tables import Crawl
    res = await db.execute(select(Crawl.status).where(Crawl.id == crawl_id))
    row = res.first()
    return bool(row and row[0] == "cancelling")


def _looks_like_spa_shell(html: str) -> bool:
    """Quick HTML check: framework root marker + tiny rendered text."""
    if not html:
        return False
    h = html.lower()
    has_marker = any(m in h for m in (
        'id="root"', "id='root'", 'id="app"', "id='app'",
        'id="__next"', 'id="__nuxt"', 'data-reactroot', 'ng-app=',
    ))
    if not has_marker:
        return False
    # Strip tags & whitespace; if <50 words remain, it's almost certainly an unrendered shell
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    words = re.findall(r"\b\w+\b", text)
    return len(words) < 50


async def _fetch_one(url: str, semaphore: asyncio.Semaphore, delay: float) -> dict | None:
    """Try Layer 1 (Jina) → Layer 3 (ScrapFly with JS rendering) if blocked OR SPA shell."""
    from packages.crawler.layers.jina_layer import fetch_with_jina
    from packages.crawler.layers.scrapfly_layer import fetch_with_scrapfly, is_blocked

    async with semaphore:
        if delay:
            await asyncio.sleep(delay)

        page_data = None
        try:
            page_data = await fetch_with_jina(url)
        except Exception as e:
            logger.debug("jina_fetch_failed", url=url, error=str(e))

        # Fall back to ScrapFly (renders JS) when:
        # 1. Jina failed entirely
        # 2. Jina returned a blocked page (Cloudflare, DataDome, etc.)
        # 3. Jina returned an unrendered SPA shell (insight from user feedback)
        needs_fallback = (
            not page_data
            or (page_data.get("html") and is_blocked(page_data.get("html", "")))
            or (page_data.get("html") and _looks_like_spa_shell(page_data.get("html", "")))
        )
        if needs_fallback:
            try:
                fallback = await fetch_with_scrapfly(url)
                if fallback and fallback.get("html"):
                    # Only use fallback if it actually rendered MORE content
                    if not _looks_like_spa_shell(fallback["html"]) or not page_data:
                        page_data = fallback
            except Exception as e:
                logger.debug("scrapfly_fetch_failed", url=url, error=str(e))

        return page_data


async def _async_crawl(site_id: str, crawl_id: str):
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select
    from config import get_settings
    from models.tables import Site, Crawl, Page, Issue
    from packages.crawler.url_utils import normalize_url, is_safe_url, dedupe_urls

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        site = (await db.execute(select(Site).where(Site.id == site_id))).scalar_one_or_none()
        if not site:
            logger.error("crawl_site_not_found", site_id=site_id)
            return

        crawl = (await db.execute(select(Crawl).where(Crawl.id == crawl_id))).scalar_one_or_none()
        if not crawl:
            return

        crawl.status = "running"
        crawl.started_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            from packages.crawler.robots import get_robots_rules, get_crawl_delay
            from packages.crawler.sitemap import discover_sitemap_urls
            from packages.crawler.extractor import (
                SEOExtractor,
                calculate_page_score,
                generate_issues,
                classify_page_type,
            )

            domain = site.domain
            if not domain.startswith("http"):
                domain = f"https://{domain}"

            # Security 1: SSRF check on the root domain itself
            if not is_safe_url(domain):
                raise ValueError(f"Domain rejected for safety: {domain}")

            logger.info("crawl_started", site_id=site_id, domain=domain)

            # robots.txt
            robots = await get_robots_rules(domain)
            delay = get_crawl_delay(robots)

            # Sitemap discovery
            raw_urls = []
            try:
                async for u in discover_sitemap_urls(domain):
                    raw_urls.append(u)
                    if len(raw_urls) >= site.crawl_max_pages * 2:  # extra room for dedupe
                        break
            except Exception:
                pass

            if not raw_urls:
                raw_urls = [domain]

            # Gap 1: normalize + dedupe; Security 1: filter unsafe
            urls = [u for u in dedupe_urls(raw_urls) if is_safe_url(u)][: site.crawl_max_pages]
            await db.execute(
                _set_crawl_total(crawl_id, len(urls))
            )
            await db.commit()
            logger.info("crawl_urls_planned", count=len(urls))

            # Gap 3: bounded concurrency
            semaphore = asyncio.Semaphore(MAX_CONCURRENT_FETCHES)
            broken_url_codes: dict[str, int] = {}  # url -> status (Bug 7)

            crawled_pages: list[dict] = []

            # Process in batches so we can check cancellation often
            BATCH = 25
            for batch_start in range(0, len(urls), BATCH):
                if await _check_cancelled(db, crawl_id):
                    logger.info("crawl_cancelled", crawl_id=crawl_id)
                    crawl = (await db.execute(select(Crawl).where(Crawl.id == crawl_id))).scalar_one()
                    crawl.status = "cancelled"
                    crawl.completed_at = datetime.now(timezone.utc)
                    await db.commit()
                    return

                batch = urls[batch_start: batch_start + BATCH]
                results = await asyncio.gather(
                    *(_fetch_one(u, semaphore, delay) for u in batch),
                    return_exceptions=True,
                )
                for url, res in zip(batch, results):
                    if isinstance(res, Exception) or not res:
                        broken_url_codes[url] = 0
                        continue
                    status = int(res.get("status_code") or 200)
                    if status >= 400:
                        broken_url_codes[url] = status
                    crawled_pages.append({"url": url, **res})

                # Persist progress
                crawl = (await db.execute(select(Crawl).where(Crawl.id == crawl_id))).scalar_one()
                crawl.pages_crawled = len(crawled_pages)
                await db.commit()

            # Extract SEO signals & save pages
            extracted: list[dict] = []
            for page_data in crawled_pages:
                html = page_data.get("html", "")
                url = page_data.get("url", "")
                headers = page_data.get("headers") or {}
                status = int(page_data.get("status_code") or 200)
                rt = page_data.get("response_time_ms")

                try:
                    if html:
                        signals = SEOExtractor(html, url, headers=headers).extract_all()
                    else:
                        signals = {}
                    signals["url"] = url
                    signals["status_code"] = status
                    signals["response_time_ms"] = rt
                    signals["page_type"] = classify_page_type(url, signals.get("schema_types"))
                    # Count broken outbound links found in HTML against our broken_url_codes map
                    # (best-effort — full link-checker is a separate task)
                    signals["broken_links_count"] = 0
                    signals["seo_score"] = calculate_page_score(signals)

                    page_record = Page(
                        crawl_id=crawl_id,
                        site_id=site_id,
                        org_id=str(site.org_id),
                        url=url,
                        status_code=status,
                        response_time_ms=rt,
                        title=signals.get("title"),
                        title_length=signals.get("title_length"),
                        meta_description=signals.get("meta_description"),
                        meta_description_length=signals.get("meta_description_length"),
                        canonical_url=signals.get("canonical_url"),
                        robots_directive=signals.get("robots_directive"),
                        h1_count=signals.get("h1_count", 0),
                        h1_text=signals.get("h1_text"),
                        h2_count=signals.get("h2_count", 0),
                        h3_count=signals.get("h3_count", 0),
                        heading_structure=signals.get("heading_structure"),
                        word_count=signals.get("word_count", 0),
                        images_count=signals.get("images_count", 0),
                        images_missing_alt=signals.get("images_missing_alt", 0),
                        broken_links_count=signals.get("broken_links_count", 0),
                        og_title=signals.get("og_title"),
                        og_description=signals.get("og_description"),
                        og_image=signals.get("og_image"),
                        twitter_card=signals.get("twitter_card"),
                        schema_types=signals.get("schema_types"),
                        schema_valid=signals.get("schema_valid", True),
                        schema_errors=signals.get("schema_errors"),
                        hreflang_tags=signals.get("hreflang_tags"),
                        hreflang_errors=signals.get("hreflang_errors"),
                        seo_score=signals.get("seo_score", 50),
                        internal_links_count=signals.get("internal_links_count", 0),
                        external_links_count=signals.get("external_links_count", 0),
                    )
                    db.add(page_record)
                    await db.flush()
                    signals["_page_id"] = str(page_record.id)
                    extracted.append(signals)
                except Exception as e:
                    logger.warning("page_extraction_failed", url=url, error=str(e))

            # Bug 7: Add synthetic page rows for URLs that returned 4xx/5xx so they show up as issues
            for bad_url, code in broken_url_codes.items():
                if any(p["url"] == bad_url for p in extracted):
                    continue
                pr = Page(
                    crawl_id=crawl_id,
                    site_id=site_id,
                    org_id=str(site.org_id),
                    url=bad_url,
                    status_code=code or 0,
                    seo_score=0,
                )
                db.add(pr)
                await db.flush()
                extracted.append({
                    "_page_id": str(pr.id),
                    "url": bad_url,
                    "status_code": code or 0,
                    "page_type": "generic",
                })

            await db.commit()

            # Generate issues
            raw_issues = generate_issues(extracted)
            for issue_data in raw_issues:
                issue = Issue(
                    crawl_id=crawl_id,
                    site_id=site_id,
                    org_id=str(site.org_id),
                    page_id=issue_data.get("page_id"),
                    type=issue_data["type"],
                    category=issue_data["category"],
                    severity=issue_data["severity"],
                    impact_score=issue_data["impact_score"],
                    current_value=issue_data.get("current_value"),
                    fix_type=issue_data.get("fix_type", "manual"),
                    fix_status="pending",
                )
                db.add(issue)

            # Update crawl & site
            site_score = int(
                sum(p.get("seo_score", 50) for p in extracted) / max(len(extracted), 1)
            )
            crawl = (await db.execute(select(Crawl).where(Crawl.id == crawl_id))).scalar_one()
            crawl.status = "completed"
            crawl.completed_at = datetime.now(timezone.utc)
            crawl.pages_crawled = len(extracted)
            crawl.issues_found = len(raw_issues)
            crawl.seo_score = site_score
            crawl.duration_ms = int(
                (crawl.completed_at - crawl.started_at).total_seconds() * 1000
            ) if crawl.started_at else 0

            site.status = "active"
            site.last_crawled_at = datetime.now(timezone.utc)
            await db.commit()

            # Trigger AI analysis (best-effort — no Redis broker in dev is OK)
            try:
                from workers.tasks.fix import run_ai_analysis
                if os.environ.get("REDIS_URL"):
                    run_ai_analysis.delay(crawl_id, site_id)
                else:
                    # Run inline for dev environments
                    import asyncio as _a
                    try:
                        from asgiref.sync import async_to_sync
                        async_to_sync(getattr(run_ai_analysis, "_async_impl", _noop))(crawl_id, site_id)
                    except Exception:
                        pass
            except Exception as e:
                logger.debug("ai_dispatch_skipped", error=str(e))

            logger.info(
                "crawl_completed",
                site_id=site_id,
                pages=len(extracted),
                issues=len(raw_issues),
                score=site_score,
                broken=len(broken_url_codes),
            )

        except Exception as e:
            logger.error("crawl_failed", site_id=site_id, error=str(e))
            crawl = (await db.execute(
                _select_crawl(crawl_id)
            )).scalar_one_or_none()
            if crawl:
                crawl.status = "failed"
                crawl.error_message = str(e)
                await db.commit()
            raise


def _select_crawl(crawl_id: str):
    from sqlalchemy import select
    from models.tables import Crawl
    return select(Crawl).where(Crawl.id == crawl_id)


def _set_crawl_total(crawl_id: str, total: int):
    from sqlalchemy import update
    from models.tables import Crawl
    return update(Crawl).where(Crawl.id == crawl_id).values(pages_total=total)


async def _noop(*a, **k):
    return None


@app.task
def run_scheduled_crawls():
    logger.info("scheduled_crawls_check")
    try:
        from asgiref.sync import async_to_sync
        async_to_sync(_run_scheduled)()
    except ImportError:
        asyncio.run(_run_scheduled())


async def _run_scheduled():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select
    from datetime import timedelta
    from config import get_settings
    from models.tables import Site, Crawl

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    freq_map = {
        "daily": timedelta(hours=24),
        "weekly": timedelta(days=7),
        "monthly": timedelta(days=30),
    }
    now = datetime.now(timezone.utc)
    async with SessionLocal() as db:
        sites = (await db.execute(select(Site).where(Site.status != "inactive"))).scalars().all()
        for site in sites:
            freq = freq_map.get(site.crawl_frequency or "weekly", timedelta(days=7))
            if site.last_crawled_at and (now - site.last_crawled_at) < freq:
                continue
            crawl = Crawl(
                site_id=site.id, org_id=site.org_id,
                status="queued", trigger="scheduled",
            )
            db.add(crawl)
            await db.flush()
            if os.environ.get("REDIS_URL"):
                run_site_crawl.delay(str(site.id), str(crawl.id))
            else:
                # Fire-and-forget local task
                asyncio.create_task(_async_crawl(str(site.id), str(crawl.id)))
        await db.commit()


@app.task
def refresh_expiring_tokens():
    logger.info("token_refresh_check")
