"""Fix tasks — AI analysis & CMS apply, end-to-end.

Celery is optional in dev (no REDIS_URL) — when celery_app fails to import we
expose a no-op decorator so the FastAPI BackgroundTasks dispatcher can call
the underlying coroutine directly via the `_async_impl` attribute.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys

# Ensure packages are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import structlog

logger = structlog.get_logger()

# ── Celery-or-noop scaffolding (mirrors workers/tasks/crawl.py) ───────────────
try:
    from workers.celery_app import app  # type: ignore
    _CELERY_AVAILABLE = True
except Exception:
    _CELERY_AVAILABLE = False

    class _NoopTask:
        def __init__(self, fn, async_impl=None):
            self.fn = fn
            self._async_impl = async_impl
        def __call__(self, *a, **kw):
            return self.fn(*a, **kw)
        def delay(self, *a, **kw):
            logger.warning("celery_unavailable_running_inline", task=self.fn.__name__)
            return self.fn(*a, **kw)
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


# ── Public Celery tasks ───────────────────────────────────────────────────────

@app.task(bind=True, max_retries=2)
def apply_ai_fix(self, issue_id: str, site_id: str):
    """Apply an AI-generated fix via the appropriate CMS adapter."""
    try:
        try:
            from asgiref.sync import async_to_sync
            return async_to_sync(_apply_ai_fix_async)(issue_id, site_id)
        except ImportError:
            return asyncio.run(_apply_ai_fix_async(issue_id, site_id))
    except Exception as exc:
        logger.error("apply_ai_fix_failed", issue_id=issue_id, error=str(exc))
        if _CELERY_AVAILABLE:
            raise self.retry(exc=exc, countdown=30)
        raise


@app.task(bind=True, max_retries=2)
def run_ai_analysis(self, crawl_id: str, site_id: str):
    """Run Claude AI analysis on crawl results to populate proposed_fix on every issue."""
    try:
        try:
            from asgiref.sync import async_to_sync
            return async_to_sync(_run_ai_analysis_async)(crawl_id, site_id)
        except ImportError:
            return asyncio.run(_run_ai_analysis_async(crawl_id, site_id))
    except Exception as exc:
        logger.error("ai_analysis_failed", crawl_id=crawl_id, error=str(exc))
        if _CELERY_AVAILABLE:
            raise self.retry(exc=exc, countdown=30)
        raise


# Expose the async impls directly for the dev BackgroundTasks dispatcher
apply_ai_fix._async_impl = lambda issue_id, site_id: _apply_ai_fix_async(issue_id, site_id)  # type: ignore
run_ai_analysis._async_impl = lambda crawl_id, site_id: _run_ai_analysis_async(crawl_id, site_id)  # type: ignore


# ── Implementation ────────────────────────────────────────────────────────────

async def _run_ai_analysis_async(crawl_id: str, site_id: str):
    """Generate a proposed fix for every auto-fixable issue in this crawl."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select
    from config import get_settings
    from models.tables import Issue, Page, Site, AiUsage
    from packages.ai_engine.engine import generate_fix
    from packages.shared.ai_safety import sanitize_html_for_ai, sanitize_field_value, validate_ai_output, UnsafeAIOutput
    from packages.shared.seo_domain import (
        FIX_STATUS_PENDING,
        FIX_STATUS_REJECTED_UNSAFE,
        issue_to_fix_field,
        normalize_issue_type,
    )

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        site = (await db.execute(select(Site).where(Site.id == site_id))).scalar_one_or_none()
        if not site:
            logger.warning("ai_analysis_site_missing", site_id=site_id)
            return

        # Only analyze auto-fixable, pending issues from this crawl
        rows = (await db.execute(
            select(Issue, Page)
            .join(Page, Page.id == Issue.page_id, isouter=True)
            .where(
                Issue.crawl_id == crawl_id,
                Issue.fix_status == FIX_STATUS_PENDING,
                Issue.fix_type == "auto",
            )
        )).all()

        logger.info("ai_analysis_starting", crawl_id=crawl_id, candidates=len(rows))
        analyzed = 0
        for issue, page in rows:
            try:
                content_excerpt = sanitize_html_for_ai(
                    (page.title or "") + " " + (page.meta_description or "") + " " + " ".join(page.h1_text or []),
                    max_len=1500,
                ) if page else ""
                fix = await generate_fix(
                    issue_type=normalize_issue_type(issue.type),
                    current_value=sanitize_field_value(issue.current_value or "", 500),
                    page_url=(page.url if page else "") or site.domain,
                    page_title=sanitize_field_value(page.title if page else "", 200),
                    h1_text=sanitize_field_value(" ".join(page.h1_text or []) if page else "", 200),
                    content_excerpt=content_excerpt,
                )

                # Validate AI output before persisting
                field = issue_to_fix_field(issue.type)
                try:
                    validated = validate_ai_output(fix.fix, field=field)
                except UnsafeAIOutput as exc:
                    logger.warning("ai_output_rejected", issue_id=str(issue.id), reason=str(exc))
                    issue.fix_status = FIX_STATUS_REJECTED_UNSAFE
                    continue

                issue.proposed_fix = validated
                issue.ai_confidence = fix.confidence
                # Tier 1 = auto-apply, 2 = one-click, 3 = manual
                if fix.tier == 3:
                    issue.fix_type = "manual"

                # Track usage if non-stub
                if fix.model_used != "none":
                    db.add(AiUsage(
                        org_id=site.org_id,
                        crawl_id=crawl_id,
                        issue_id=issue.id,
                        model=fix.model_used,
                        prompt_tokens=fix.input_tokens,
                        completion_tokens=fix.output_tokens,
                        total_tokens=fix.input_tokens + fix.output_tokens,
                        cost_usd=fix.cost_usd,
                        task_type="fix_generation",
                    ))
                analyzed += 1
            except Exception as exc:
                logger.warning("ai_fix_gen_failed", issue_id=str(issue.id), error=str(exc))

        await db.commit()
        logger.info("ai_analysis_complete", crawl_id=crawl_id, analyzed=analyzed)


async def _apply_ai_fix_async(issue_id: str, site_id: str) -> dict:
    """Push an approved AI fix to the live CMS via the correct adapter."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select
    from datetime import datetime, timezone
    from config import get_settings
    from models.tables import ChangeLog, Issue, Page, PageSource, Site
    from packages.cms_adapters import get_adapter
    from packages.shared.ai_safety import validate_ai_output, UnsafeAIOutput
    from packages.shared.seo_domain import (
        FIX_STATUS_APPLY_FAILED,
        FIX_STATUS_DEPLOYED,
        FIX_STATUS_REJECTED_UNSAFE,
        issue_can_auto_deploy,
        issue_to_fix_field,
    )

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        issue = (await db.execute(select(Issue).where(Issue.id == issue_id))).scalar_one_or_none()
        if not issue or not issue.proposed_fix:
            return {"success": False, "message": "Issue or proposed fix missing"}

        site = (await db.execute(select(Site).where(Site.id == site_id))).scalar_one_or_none()
        if not site:
            return {"success": False, "message": "Site not found"}

        page = None
        if issue.page_id:
            page = (await db.execute(select(Page).where(Page.id == issue.page_id))).scalar_one_or_none()

        field = issue_to_fix_field(issue.type)
        if not issue_can_auto_deploy(issue.type, site.connection_type):
            issue.fix_status = FIX_STATUS_APPLY_FAILED
            db.add(ChangeLog(
                org_id=site.org_id,
                site_id=site.id,
                issue_id=issue.id,
                action="fix_deploy_failed",
                actor_type="system",
                old_value=issue.current_value,
                new_value=issue.proposed_fix,
                extra_metadata={
                    "reason": "unsupported_field_or_connection",
                    "connection_type": site.connection_type,
                    "field": field,
                },
            ))
            await db.commit()
            return {"success": False, "message": f"{site.connection_type} cannot deploy {field} fixes automatically"}

        # Re-validate before pushing live
        try:
            new_value = validate_ai_output(issue.proposed_fix, field=field)
        except UnsafeAIOutput as exc:
            issue.fix_status = FIX_STATUS_REJECTED_UNSAFE
            await db.commit()
            return {"success": False, "message": f"Refused unsafe AI output: {exc}"}

        # Decrypt creds and build the right adapter
        try:
            creds = _decrypt_site_creds(str(site.org_id), site)
            adapter = get_adapter(site.connection_type, **_adapter_kwargs(site, creds))
        except Exception as exc:
            from packages.shared.seo_domain import FIX_STATUS_APPLY_FAILED
            issue.fix_status = FIX_STATUS_APPLY_FAILED
            db.add(ChangeLog(
                org_id=site.org_id,
                site_id=site.id,
                issue_id=issue.id,
                action="fix_deploy_failed",
                actor_type="system",
                old_value=issue.current_value,
                new_value=issue.proposed_fix,
                extra_metadata={"reason": "adapter_setup_failed", "message": str(exc)},
            ))
            await db.commit()
            return {"success": False, "message": f"Adapter setup failed: {exc}"}

        cms_page_id = await _resolve_cms_page_id(
            db=db,
            site=site,
            page=page,
            adapter=adapter,
            page_source_model=PageSource,
        )
        if not cms_page_id:
            issue.fix_status = FIX_STATUS_APPLY_FAILED
            db.add(ChangeLog(
                org_id=site.org_id,
                site_id=site.id,
                issue_id=issue.id,
                action="fix_deploy_failed",
                actor_type="system",
                old_value=issue.current_value,
                new_value=new_value,
                extra_metadata={
                    "reason": "page_source_not_found",
                    "connection_type": site.connection_type,
                    "field": field,
                },
            ))
            await db.commit()
            return {"success": False, "message": "Unable to map crawled page to CMS resource"}

        try:
            result = await adapter.apply_fix(cms_page_id, field, new_value)
        except Exception as exc:
            logger.exception("apply_fix_adapter_error", issue_id=str(issue.id))
            issue.fix_status = FIX_STATUS_APPLY_FAILED
            db.add(ChangeLog(
                org_id=site.org_id,
                site_id=site.id,
                issue_id=issue.id,
                action="fix_deploy_failed",
                actor_type="system",
                old_value=issue.current_value,
                new_value=new_value,
                extra_metadata={"reason": "adapter_error", "message": str(exc)},
            ))
            await db.commit()
            return {"success": False, "message": f"Adapter error: {exc}"}

        if result.success:
            issue.fix_status = FIX_STATUS_DEPLOYED
            issue.applied_at = datetime.now(timezone.utc)
            if not issue.rollback_value:
                issue.rollback_value = result.rollback_value or issue.current_value
            db.add(ChangeLog(
                org_id=site.org_id,
                site_id=site.id,
                issue_id=issue.id,
                action="fix_deployed",
                actor_type="system",
                old_value=issue.current_value,
                new_value=new_value,
                extra_metadata={
                    "connection_type": site.connection_type,
                    "field": field,
                    "source_page_id": cms_page_id,
                },
            ))
        else:
            issue.fix_status = FIX_STATUS_APPLY_FAILED
            db.add(ChangeLog(
                org_id=site.org_id,
                site_id=site.id,
                issue_id=issue.id,
                action="fix_deploy_failed",
                actor_type="system",
                old_value=issue.current_value,
                new_value=new_value,
                extra_metadata={
                    "connection_type": site.connection_type,
                    "field": field,
                    "source_page_id": cms_page_id,
                    "message": result.message,
                },
            ))

        await db.commit()
        return {"success": result.success, "message": result.message}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _issue_to_field(issue_type: str) -> str:
    """Map an issue type to the CMS field that the AI fix should write to."""
    from packages.shared.seo_domain import issue_to_fix_field
    return issue_to_fix_field(issue_type)


def _decrypt_site_creds(org_id: str, site) -> dict:
    """Decrypt the JSON-encoded credential blob stored on the site."""
    if not site.cms_token_encrypted or not site.cms_token_iv:
        return {}
    from packages.shared.encryption import decrypt_credential
    plaintext = decrypt_credential(org_id, site.cms_token_encrypted, site.cms_token_iv)
    try:
        return json.loads(plaintext)
    except json.JSONDecodeError:
        # Legacy path: the field used to hold a single token string
        return {"access_token": plaintext}


def _adapter_kwargs(site, creds: dict) -> dict:
    """Build the keyword args expected by each adapter's constructor."""
    ct = site.connection_type
    if ct == "wordpress":
        return {
            "site_url": site.cms_endpoint or site.domain,
            "username": creds.get("username", ""),
            "app_password": creds.get("app_password", ""),
        }
    if ct == "shopify":
        return {
            "shop_domain": creds.get("shop_domain") or site.cms_endpoint or site.domain,
            "access_token": creds.get("access_token", ""),
        }
    if ct == "webflow":
        return {
            "site_id": creds.get("site_id", ""),
            "token": creds.get("token", ""),
        }
    if ct == "github":
        return {
            "owner": creds.get("owner") or (site.github_repo or "").split("/")[0],
            "repo": creds.get("repo") or (site.github_repo or "").split("/", 1)[-1],
            "token": creds.get("token", ""),
            "branch": site.github_branch or "main",
        }
    if ct == "snippet":
        return {"site_token": str(site.snippet_token)}
    return {"domain": site.domain}


async def _resolve_cms_page_id(db, site, page, adapter, page_source_model) -> str:
    """Resolve the real CMS resource ID for a crawled page."""
    from datetime import datetime, timezone
    from sqlalchemy import select
    from urllib.parse import urlparse
    from packages.crawler.url_utils import normalize_url, urls_match_resource

    if not page:
        return ""

    normalized_public_url = normalize_url(page.url)
    existing = (await db.execute(
        select(page_source_model).where(
            page_source_model.site_id == site.id,
            page_source_model.public_url == normalized_public_url,
        )
    )).scalar_one_or_none()
    if existing:
        if existing.page_id != page.id:
            existing.page_id = page.id
            existing.last_synced_at = datetime.now(timezone.utc)
            await db.flush()
        return existing.source_page_id

    candidates = await adapter.list_pages(limit=max(int(site.crawl_max_pages or 500), 500))
    site_base = site.domain if str(site.domain).startswith("http") else f"https://{site.domain}"

    for candidate in candidates:
        if not urls_match_resource(page.url, candidate.url, site_domain=site_base):
            continue

        source_path = None
        raw = candidate.raw or {}
        if isinstance(raw, dict):
            source_path = raw.get("path") or raw.get("slug")
        if not source_path and candidate.url:
            parsed_candidate = urlparse(candidate.url)
            source_path = parsed_candidate.path or None

        source = page_source_model(
            site_id=site.id,
            org_id=site.org_id,
            page_id=page.id,
            public_url=normalized_public_url,
            source_page_id=str(candidate.id),
            source_path=source_path,
            source_url=candidate.url or None,
            connection_type=site.connection_type,
            source_metadata=raw if isinstance(raw, dict) else None,
            last_synced_at=datetime.now(timezone.utc),
        )
        db.add(source)
        await db.flush()
        return str(candidate.id)

    return ""
