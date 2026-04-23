"""Crawl tasks — multi-layer crawler with SEO extraction and issue generation."""
from __future__ import annotations

import asyncio
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import structlog

# Ensure packages are importable from the workers directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

logger = structlog.get_logger()

try:
    from workers.celery_app import app  # type: ignore
    _CELERY_AVAILABLE = True
except Exception:
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

            if a and callable(a[0]) and not kw:
                return _NoopTask(a[0])
            return deco

    app = _NoopApp()  # type: ignore


MAX_CONCURRENT_FETCHES = 5


@app.task(bind=True, max_retries=3)
def run_site_crawl(self, site_id: str, crawl_id: str):
    """Celery entrypoint — wraps async crawl using asgiref when available."""
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
    from sqlalchemy import select
    from models.tables import Crawl

    res = await db.execute(select(Crawl.status).where(Crawl.id == crawl_id))
    row = res.first()
    return bool(row and row[0] == "cancelling")


def _looks_like_spa_shell(html: str) -> bool:
    if not html:
        return False
    lowered = html.lower()
    has_marker = any(
        marker in lowered
        for marker in (
            'id="root"',
            "id='root'",
            'id="app"',
            "id='app'",
            'id="__next"',
            'id="__nuxt"',
            "data-reactroot",
            "ng-app=",
        )
    )
    if not has_marker:
        return False

    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return len(re.findall(r"\b\w+\b", text)) < 50


async def _conditional_get_unchanged(url: str, etag: str | None, last_modified: str | None) -> bool:
    if not etag and not last_modified:
        return False

    from packages.crawler.url_utils import is_safe_url

    if not is_safe_url(url):
        return False

    headers: dict[str, str] = {"User-Agent": "AutoSEO/1.0 (+https://autoseo.app)"}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    try:
        import httpx

        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.head(url, headers=headers)
            return is_safe_url(str(resp.url)) and resp.status_code == 304
    except Exception:
        return False


async def _fetch_one(
    url: str,
    semaphore: asyncio.Semaphore,
    delay: float,
    cached_headers: dict[str, tuple[str | None, str | None]] | None = None,
) -> dict | None:
    from packages.crawler.layers.jina_layer import fetch_with_jina
    from packages.crawler.layers.scrapfly_layer import fetch_with_scrapfly, is_blocked

    async with semaphore:
        if delay:
            await asyncio.sleep(delay)

        if cached_headers and url in cached_headers:
            etag, last_modified = cached_headers[url]
            if await _conditional_get_unchanged(url, etag, last_modified):
                return {"url": url, "status_code": 304, "headers": {}, "html": "", "_unchanged": True}

        page_data = None
        try:
            page_data = await fetch_with_jina(url)
        except Exception as exc:
            logger.debug("jina_fetch_failed", url=url, error=str(exc))

        needs_fallback = (
            not page_data
            or (page_data.get("html") and is_blocked(page_data.get("html", "")))
            or (page_data.get("html") and _looks_like_spa_shell(page_data.get("html", "")))
        )
        if needs_fallback:
            try:
                fallback = await fetch_with_scrapfly(url)
                if fallback and fallback.get("html"):
                    if not _looks_like_spa_shell(fallback["html"]) or not page_data:
                        page_data = fallback
            except Exception as exc:
                logger.debug("scrapfly_fetch_failed", url=url, error=str(exc))

        return page_data


async def _async_crawl(site_id: str, crawl_id: str):
    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from config import get_settings
    from models.tables import Crawl, Issue, Page, Site
    from packages.crawler.url_utils import dedupe_urls, is_safe_url
    from packages.shared.db_lock import advisory_lock
    from packages.shared.seo_domain import normalize_issue_type

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with advisory_lock(engine, "site-crawl", site_id) as lock_acquired:
            if not lock_acquired:
                async with SessionLocal() as db:
                    crawl = (await db.execute(select(Crawl).where(Crawl.id == crawl_id))).scalar_one_or_none()
                    if crawl:
                        crawl.status = "failed"
                        crawl.error_message = "Another crawl already holds the site lock"
                        await db.commit()
                return

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
                    from packages.crawler.extractor import (
                        SEOExtractor,
                        calculate_page_score,
                        classify_page_type,
                        generate_issues,
                    )
                    from packages.crawler.robots import get_crawl_delay, get_robots_rules
                    from packages.crawler.sitemap import discover_sitemap_urls

                    domain = site.domain if str(site.domain).startswith("http") else f"https://{site.domain}"
                    if not is_safe_url(domain):
                        raise ValueError(f"Domain rejected for safety: {domain}")

                    logger.info("crawl_started", site_id=site_id, domain=domain)

                    robots = await get_robots_rules(domain)
                    delay = get_crawl_delay(robots)

                    raw_urls: list[str] = []
                    try:
                        async for discovered_url in discover_sitemap_urls(domain):
                            raw_urls.append(discovered_url)
                            if len(raw_urls) >= site.crawl_max_pages * 2:
                                break
                    except Exception:
                        pass

                    if not raw_urls:
                        raw_urls = [domain]

                    urls = [url for url in dedupe_urls(raw_urls) if is_safe_url(url)][: site.crawl_max_pages]
                    await db.execute(_set_crawl_total(crawl_id, len(urls)))
                    await db.commit()
                    logger.info("crawl_urls_planned", count=len(urls))

                    semaphore = asyncio.Semaphore(MAX_CONCURRENT_FETCHES)
                    broken_url_codes: dict[str, int] = {}

                    cached_headers: dict[str, tuple[str | None, str | None]] = {}
                    rows = (
                        await db.execute(
                            select(Page.url, Page.etag, Page.last_modified)
                            .where(Page.site_id == site_id, Page.url.in_(urls))
                            .order_by(Page.created_at.desc())
                        )
                    ).all()
                    for row in rows:
                        if row.url not in cached_headers:
                            cached_headers[row.url] = (row.etag, row.last_modified)

                    prior_pages_by_url: dict[str, Page] = {}
                    if cached_headers:
                        prior_rows = (
                            await db.execute(
                                select(Page)
                                .where(Page.site_id == site_id, Page.url.in_(list(cached_headers.keys())))
                                .order_by(Page.created_at.desc())
                            )
                        ).scalars().all()
                        for prior_page in prior_rows:
                            prior_pages_by_url.setdefault(prior_page.url, prior_page)

                    crawled_pages: list[dict] = []
                    batch_size = 25
                    for batch_start in range(0, len(urls), batch_size):
                        if await _check_cancelled(db, crawl_id):
                            logger.info("crawl_cancelled", crawl_id=crawl_id)
                            crawl = (await db.execute(select(Crawl).where(Crawl.id == crawl_id))).scalar_one()
                            crawl.status = "cancelled"
                            crawl.completed_at = datetime.now(timezone.utc)
                            await db.commit()
                            return

                        batch = urls[batch_start: batch_start + batch_size]
                        results = await asyncio.gather(
                            *(_fetch_one(url, semaphore, delay, cached_headers) for url in batch),
                            return_exceptions=True,
                        )
                        for url, result in zip(batch, results):
                            if isinstance(result, Exception) or not result:
                                broken_url_codes[url] = 0
                                continue
                            status_code = int(result.get("status_code") or 200)
                            if status_code >= 400:
                                broken_url_codes[url] = status_code
                            crawled_pages.append({"url": url, **result})

                        crawl = (await db.execute(select(Crawl).where(Crawl.id == crawl_id))).scalar_one()
                        crawl.pages_crawled = len(crawled_pages)
                        await db.commit()

                    extracted: list[dict] = []
                    for page_data in crawled_pages:
                        html = page_data.get("html", "")
                        url = page_data.get("url", "")
                        headers = page_data.get("headers") or {}
                        status_code = int(page_data.get("status_code") or 200)
                        response_time_ms = page_data.get("response_time_ms")

                        try:
                            if page_data.get("_unchanged") and url in prior_pages_by_url:
                                prior = prior_pages_by_url[url]
                                cloned = Page(
                                    crawl_id=crawl_id,
                                    site_id=site_id,
                                    org_id=str(site.org_id),
                                    url=url,
                                    status_code=prior.status_code,
                                    response_time_ms=prior.response_time_ms,
                                    title=prior.title,
                                    title_length=prior.title_length,
                                    meta_description=prior.meta_description,
                                    meta_description_length=prior.meta_description_length,
                                    canonical_url=prior.canonical_url,
                                    robots_directive=prior.robots_directive,
                                    h1_count=prior.h1_count,
                                    h1_text=prior.h1_text,
                                    h2_count=prior.h2_count,
                                    h3_count=prior.h3_count,
                                    heading_structure=prior.heading_structure,
                                    word_count=prior.word_count,
                                    images_count=prior.images_count,
                                    images_missing_alt=prior.images_missing_alt,
                                    broken_links_count=prior.broken_links_count,
                                    og_title=prior.og_title,
                                    og_description=prior.og_description,
                                    og_image=prior.og_image,
                                    twitter_card=prior.twitter_card,
                                    schema_types=prior.schema_types,
                                    schema_valid=prior.schema_valid,
                                    schema_errors=prior.schema_errors,
                                    hreflang_tags=prior.hreflang_tags,
                                    hreflang_errors=prior.hreflang_errors,
                                    seo_score=prior.seo_score,
                                    internal_links_count=prior.internal_links_count,
                                    external_links_count=prior.external_links_count,
                                    etag=prior.etag,
                                    last_modified=prior.last_modified,
                                )
                                db.add(cloned)
                                await db.flush()
                                extracted.append(
                                    {
                                        "_page_id": str(cloned.id),
                                        "url": url,
                                        "title": prior.title,
                                        "h1_text": prior.h1_text,
                                        "seo_score": prior.seo_score or 50,
                                        "page_type": classify_page_type(url, prior.schema_types),
                                    }
                                )
                                continue

                            signals = SEOExtractor(html, url, headers=headers).extract_all() if html else {}
                            signals["url"] = url
                            signals["status_code"] = status_code
                            signals["response_time_ms"] = response_time_ms
                            signals["page_type"] = classify_page_type(url, signals.get("schema_types"))
                            signals["broken_links_count"] = 0
                            signals["seo_score"] = calculate_page_score(signals)

                            page_record = Page(
                                crawl_id=crawl_id,
                                site_id=site_id,
                                org_id=str(site.org_id),
                                url=url,
                                status_code=status_code,
                                response_time_ms=response_time_ms,
                                etag=(headers.get("etag") if isinstance(headers, dict) else None),
                                last_modified=(headers.get("last-modified") if isinstance(headers, dict) else None),
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
                                content_hash=signals.get("content_hash"),
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
                        except Exception as exc:
                            logger.warning("page_extraction_failed", url=url, error=str(exc))

                    for bad_url, status_code in broken_url_codes.items():
                        if any(page["url"] == bad_url for page in extracted):
                            continue
                        bad_page = Page(
                            crawl_id=crawl_id,
                            site_id=site_id,
                            org_id=str(site.org_id),
                            url=bad_url,
                            status_code=status_code or 0,
                            seo_score=0,
                        )
                        db.add(bad_page)
                        await db.flush()
                        extracted.append(
                            {
                                "_page_id": str(bad_page.id),
                                "url": bad_url,
                                "status_code": status_code or 0,
                                "page_type": "generic",
                            }
                        )

                    await db.commit()

                    raw_issues = generate_issues(extracted)
                    try:
                        from packages.crawler.cannibalization import detect_cannibalization

                        raw_issues.extend(detect_cannibalization(extracted))
                    except Exception as exc:
                        logger.debug("cannibalization_detect_failed", error=str(exc))

                    try:
                        buckets: dict[str, list[dict]] = {}
                        for page in extracted:
                            content_hash = page.get("content_hash")
                            if not content_hash or page.get("word_count", 0) < 50:
                                continue
                            buckets.setdefault(content_hash, []).append(page)
                        for _, group in buckets.items():
                            if len(group) < 2:
                                continue
                            sample_urls = [g.get("url") for g in group[:5]]
                            for page in group:
                                raw_issues.append(
                                    {
                                        "page_id": page.get("_page_id"),
                                        "type": "duplicate_content",
                                        "category": "content",
                                        "severity": "high",
                                        "impact_score": 70,
                                        "current_value": f"{len(group)} pages share identical content (e.g. {', '.join(u for u in sample_urls if u)})",
                                        "fix_type": "manual",
                                    }
                                )
                    except Exception as exc:
                        logger.debug("duplicate_detect_failed", error=str(exc))

                    deduped_issues: list[dict] = []
                    seen_issue_keys: set[tuple[str, str, str]] = set()
                    for issue_data in raw_issues:
                        issue_data["type"] = normalize_issue_type(issue_data["type"])
                        key = (
                            str(issue_data.get("page_id") or ""),
                            str(issue_data["type"]),
                            str(issue_data.get("current_value") or ""),
                        )
                        if key in seen_issue_keys:
                            continue
                        seen_issue_keys.add(key)
                        deduped_issues.append(issue_data)

                    for issue_data in deduped_issues:
                        db.add(
                            Issue(
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
                        )

                    site_score_value = (
                        await db.execute(
                            select(func.avg(Page.seo_score)).where(
                                Page.crawl_id == crawl_id,
                                Page.seo_score.isnot(None),
                            )
                        )
                    ).scalar()
                    site_score = int(round(float(site_score_value or 0)))

                    crawl = (await db.execute(select(Crawl).where(Crawl.id == crawl_id))).scalar_one()
                    crawl.status = "completed"
                    crawl.completed_at = datetime.now(timezone.utc)
                    crawl.pages_crawled = len(extracted)
                    crawl.issues_found = len(deduped_issues)
                    crawl.seo_score = site_score
                    crawl.duration_ms = (
                        int((crawl.completed_at - crawl.started_at).total_seconds() * 1000)
                        if crawl.started_at
                        else 0
                    )

                    site.status = "active" if getattr(site, "ownership_verified", False) else "pending_verification"
                    site.last_crawled_at = datetime.now(timezone.utc)
                    await db.commit()

                    try:
                        from workers.tasks.fix import run_ai_analysis

                        if os.environ.get("REDIS_URL"):
                            run_ai_analysis.delay(crawl_id, site_id)
                        else:
                            try:
                                from asgiref.sync import async_to_sync

                                async_to_sync(getattr(run_ai_analysis, "_async_impl", _noop))(crawl_id, site_id)
                            except Exception:
                                pass
                    except Exception as exc:
                        logger.debug("ai_dispatch_skipped", error=str(exc))

                    logger.info(
                        "crawl_completed",
                        site_id=site_id,
                        pages=len(extracted),
                        issues=len(deduped_issues),
                        score=site_score,
                        broken=len(broken_url_codes),
                    )
                except Exception as exc:
                    logger.error("crawl_failed", site_id=site_id, error=str(exc))
                    crawl = (await db.execute(_select_crawl(crawl_id))).scalar_one_or_none()
                    if crawl:
                        crawl.status = "failed"
                        crawl.error_message = str(exc)
                        await db.commit()
                    raise
    finally:
        await engine.dispose()


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
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from config import get_settings
    from models.tables import Crawl, Site

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
            crawl = Crawl(site_id=site.id, org_id=site.org_id, status="queued", trigger="scheduled")
            db.add(crawl)
            await db.flush()
            if os.environ.get("REDIS_URL"):
                run_site_crawl.delay(str(site.id), str(crawl.id))
            else:
                asyncio.create_task(_async_crawl(str(site.id), str(crawl.id)))
        await db.commit()
    await engine.dispose()


@app.task
def refresh_expiring_tokens():
    logger.info("token_refresh_check")
