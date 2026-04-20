"""Crawl tasks — 4-layer crawler with SEO signal extraction and issue generation."""
import asyncio
import sys
import os
from datetime import datetime, timezone

import structlog

# Ensure packages are importable from the workers directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from workers.celery_app import app

logger = structlog.get_logger()


@app.task(bind=True, max_retries=3)
def run_site_crawl(self, site_id: str, crawl_id: str):
    """Run a full site crawl with the 4-layer crawler architecture."""
    try:
        asyncio.run(_async_crawl(site_id, crawl_id))
    except Exception as exc:
        logger.error("crawl_task_failed", site_id=site_id, crawl_id=crawl_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60)


async def _async_crawl(site_id: str, crawl_id: str):
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select, update
    from config import get_settings
    from models.tables import Site, Crawl, Page, Issue

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        # Load site
        site = (await db.execute(select(Site).where(Site.id == site_id))).scalar_one_or_none()
        if not site:
            logger.error("crawl_site_not_found", site_id=site_id)
            return

        crawl = (await db.execute(select(Crawl).where(Crawl.id == crawl_id))).scalar_one_or_none()
        if not crawl:
            return

        # Mark crawl as running
        crawl.status = "running"
        crawl.started_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            from packages.crawler.robots import get_robots_rules, get_crawl_delay
            from packages.crawler.sitemap import discover_sitemap_urls
            from packages.crawler.extractor import SEOExtractor, calculate_page_score, generate_issues
            from packages.crawler.layers.jina_layer import fetch_with_jina
            from packages.crawler.layers.scrapfly_layer import fetch_with_scrapfly, is_blocked

            domain = site.domain
            if not domain.startswith("http"):
                domain = f"https://{domain}"

            logger.info("crawl_started", site_id=site_id, domain=domain)

            # Step 1: robots.txt
            robots = await get_robots_rules(domain)
            delay = get_crawl_delay(robots)

            # Step 2: Get URL list from sitemap
            sitemap_urls = []
            try:
                async for url in discover_sitemap_urls(domain):
                    sitemap_urls.append(url)
                    if len(sitemap_urls) >= site.crawl_max_pages:
                        break
            except Exception:
                pass

            if not sitemap_urls:
                sitemap_urls = [domain]

            logger.info("crawl_urls_discovered", count=len(sitemap_urls), source="sitemap")

            # Step 3: Crawl each URL with tiered fallback
            crawled_pages = []
            for url in sitemap_urls[:site.crawl_max_pages]:
                page_data = None

                # Layer 1: Jina (fast)
                try:
                    page_data = await fetch_with_jina(url)
                except Exception:
                    pass

                # Layer 3: ScrapFly if blocked
                if not page_data or (page_data.get("html") and is_blocked(page_data.get("html", ""))):
                    try:
                        page_data = await fetch_with_scrapfly(url)
                    except Exception:
                        pass

                if page_data:
                    crawled_pages.append({"url": url, "html": page_data.get("html", ""), **page_data})

                await asyncio.sleep(delay)

            # Step 4: Extract SEO signals and save pages
            extracted = []
            for page_data in crawled_pages:
                html = page_data.get("html", "")
                url = page_data.get("url", "")
                if not html:
                    continue
                try:
                    signals = SEOExtractor(html, url).extract_all()
                    signals["seo_score"] = calculate_page_score(signals)
                    signals["url"] = url
                    signals["status_code"] = page_data.get("status_code", 200)

                    page_record = Page(
                        crawl_id=crawl_id,
                        site_id=site_id,
                        org_id=str(site.org_id),
                        url=url,
                        status_code=signals.get("status_code", 200),
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

            await db.commit()

            # Step 5: Generate issues
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

            # Step 6: Update crawl as completed
            site_score = int(sum(p.get("seo_score", 50) for p in extracted) / max(len(extracted), 1))
            crawl.status = "completed"
            crawl.completed_at = datetime.now(timezone.utc)
            crawl.pages_crawled = len(extracted)
            crawl.issues_found = len(raw_issues)
            crawl.seo_score = site_score
            crawl.duration_ms = int(
                (crawl.completed_at - crawl.started_at).total_seconds() * 1000
            ) if crawl.started_at else 0

            # Update site status and last crawled
            site.status = "active"
            site.last_crawled_at = datetime.now(timezone.utc)

            await db.commit()

            # Step 7: Trigger AI analysis
            from workers.tasks.fix import run_ai_analysis
            run_ai_analysis.delay(crawl_id, site_id)

            logger.info(
                "crawl_completed",
                site_id=site_id,
                pages=len(extracted),
                issues=len(raw_issues),
                score=site_score,
            )

        except Exception as e:
            logger.error("crawl_failed", site_id=site_id, error=str(e))
            crawl.status = "failed"
            crawl.error_message = str(e)
            await db.commit()
            raise


@app.task
def run_scheduled_crawls():
    """Run scheduled crawls for all sites due for re-crawl."""
    logger.info("scheduled_crawls_check")
    asyncio.run(_run_scheduled())


async def _run_scheduled():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select
    from datetime import timedelta
    from config import get_settings
    from models.tables import Site, Crawl
    import uuid

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
                site_id=site.id,
                org_id=site.org_id,
                status="queued",
                trigger="scheduled",
            )
            db.add(crawl)
            await db.flush()
            run_site_crawl.delay(str(site.id), str(crawl.id))
        await db.commit()


@app.task
def refresh_expiring_tokens():
    """Refresh OAuth tokens that are about to expire."""
    logger.info("token_refresh_check")
