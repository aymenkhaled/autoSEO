"""Report and monitoring tasks."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

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


def _aware(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


@app.task
def send_weekly_digest(org_id: str):
    """Send a simple weekly SEO digest email when Resend is configured."""
    logger.info("weekly_digest_started", org_id=org_id)
    try:
        from asgiref.sync import async_to_sync

        async_to_sync(_send_weekly_digest_async)(org_id)
    except ImportError:
        asyncio.run(_send_weekly_digest_async(org_id))


async def _send_weekly_digest_async(org_id: str):
    from config import get_settings
    from models.tables import Organization, Site, User
    from services.opportunities import site_opportunities

    settings = get_settings()
    if not settings.RESEND_API_KEY:
        logger.info("weekly_digest_skipped_resend_missing", org_id=org_id)
        return

    engine = create_async_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with SessionLocal() as db:
            org = await db.get(Organization, org_id)
            if not org:
                return
            users = (await db.execute(select(User).where(User.org_id == org_id))).scalars().all()
            recipients = [user.email for user in users if user.email]
            if not recipients:
                return
            sites = (await db.execute(select(Site).where(Site.org_id == org_id).limit(10))).scalars().all()
            lines = [f"Weekly AutoSEO digest for {org.name}", ""]
            for site in sites:
                opportunities = await site_opportunities(db, site=site)
                top = opportunities["opportunities"][0] if opportunities["opportunities"] else None
                lines.append(f"- {site.name}: {top['title'] if top else 'No open opportunities'}")
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                    json={
                        "from": "AutoSEO <digest@autoseo.app>",
                        "to": recipients,
                        "subject": "Your weekly AutoSEO digest",
                        "text": "\n".join(lines),
                    },
                )
                response.raise_for_status()
    finally:
        await engine.dispose()


@app.task
def run_scheduled_monitoring():
    """Refresh connected monitoring sources on a conservative daily cadence."""
    logger.info("scheduled_monitoring_started")
    try:
        from asgiref.sync import async_to_sync

        async_to_sync(_run_scheduled_monitoring_async)()
    except ImportError:
        asyncio.run(_run_scheduled_monitoring_async())


async def _run_scheduled_monitoring_async():
    from config import get_settings
    from models.tables import GoogleAnalyticsConnection, PageSpeedRun, SearchConsoleConnection, Site
    from services.google_analytics import sync_site_google_analytics
    from services.pagespeed import default_pages_for_site, run_pagespeed_check
    from services.search_console import sync_site_search_console
    from services.snippet_insights import compute_snippet_insights

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    now = datetime.now(timezone.utc)

    try:
        async with SessionLocal() as db:
            sites = (await db.execute(select(Site).where(Site.status != "inactive"))).scalars().all()
            for site in sites:
                gsc = (
                    await db.execute(select(SearchConsoleConnection).where(SearchConsoleConnection.site_id == site.id))
                ).scalar_one_or_none()
                if gsc and (not gsc.last_sync_at or now - _aware(gsc.last_sync_at) > timedelta(hours=24)):
                    await sync_site_search_console(db, settings, site=site, connection=gsc, days=90, inspect_limit=5)

                ga = (
                    await db.execute(select(GoogleAnalyticsConnection).where(GoogleAnalyticsConnection.site_id == site.id))
                ).scalar_one_or_none()
                if ga and (not ga.last_sync_at or now - _aware(ga.last_sync_at) > timedelta(hours=24)):
                    await sync_site_google_analytics(db, settings, site=site, connection=ga, days=90)

                await compute_snippet_insights(db, site=site)

                latest_pagespeed = (
                    await db.execute(
                        select(PageSpeedRun)
                        .where(PageSpeedRun.site_id == site.id)
                        .order_by(PageSpeedRun.checked_at.desc())
                        .limit(1)
                    )
                ).scalar_one_or_none()
                if not latest_pagespeed or now - _aware(latest_pagespeed.checked_at) > timedelta(days=7):
                    for url in await default_pages_for_site(db, site=site, limit=1):
                        await run_pagespeed_check(db, settings, site=site, url=url, strategy="mobile")
    finally:
        await engine.dispose()


@app.task
def generate_pdf_report(crawl_id: str, site_id: str):
    """Placeholder for PDF rendering; on-demand structured reports work today."""
    logger.info("pdf_report_started", crawl_id=crawl_id, site_id=site_id)
