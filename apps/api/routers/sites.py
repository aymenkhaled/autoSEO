"""Sites router — CRUD operations for managed sites."""
import secrets
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete, or_
from uuid import UUID
from typing import Optional

from dependencies import get_db, get_current_user
from schemas.auth import AuthContext
from schemas.site import SiteCreate, SiteUpdate, SiteResponse, SiteListResponse
from models.tables import (
    AiUsage,
    AnalyticsPageMetric,
    AiVisibilityPrompt,
    AiVisibilityRun,
    AutopilotRun,
    Backlink,
    ChangeLog,
    ClientSite,
    Competitor,
    CompetitorPageComparison,
    ContentBrief,
    Crawl,
    CrawlLogEntry,
    CrawlLogImport,
    FixProofSnapshot,
    FixVersion,
    GoogleAnalyticsConnection,
    GoogleAnalyticsSyncRun,
    IndexNowKey,
    IndexNowSubmission,
    Issue,
    IssueComment,
    Keyword,
    KeywordProviderSyncRun,
    KeywordRanking,
    Page,
    PageSource,
    PageSpeedRun,
    ReportShareLink,
    ScheduledReport,
    SearchConsoleConnection,
    SearchConsoleInspection,
    SearchConsolePageMetric,
    SearchConsoleQueryMetric,
    SearchConsoleSitemap,
    SearchConsoleSyncRun,
    Site,
    SiteOpportunity,
    SnippetEvent,
    SnippetInsight,
)
from packages.crawler.url_utils import is_safe_url
from packages.shared.readiness import connection_status_payload, site_setup_payload
from packages.shared.seo_domain import FIX_STATUS_DEPLOYED, FIX_STATUS_DEPLOYED_AFTER_MERGE, FIX_STATUS_ROLLED_BACK
from services.opportunities import site_opportunities

router = APIRouter(tags=["sites"])

_ACTIVE_CRAWL_STATUSES = ("queued", "running", "cancelling")


def _delete_count(result) -> int:
    return int(result.rowcount or 0)


async def _active_site_crawl(db: AsyncSession, site_id: UUID, org_id: UUID) -> Crawl | None:
    return (
        await db.execute(
            select(Crawl)
            .where(
                Crawl.site_id == site_id,
                Crawl.org_id == org_id,
                Crawl.status.in_(_ACTIVE_CRAWL_STATUSES),
            )
            .order_by(Crawl.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _delete_site_records(db: AsyncSession, site_id: UUID, org_id: UUID) -> dict[str, int]:
    issue_ids = select(Issue.id).where(Issue.site_id == site_id, Issue.org_id == org_id)

    counts = {
        "issue_comments": _delete_count(
            await db.execute(delete(IssueComment).where(IssueComment.issue_id.in_(issue_ids)))
        ),
        "fix_versions": _delete_count(
            await db.execute(delete(FixVersion).where(FixVersion.site_id == site_id, FixVersion.org_id == org_id))
        ),
        "ai_usage": _delete_count(
            await db.execute(
                delete(AiUsage).where(
                    AiUsage.org_id == org_id,
                    or_(
                        AiUsage.crawl_id.in_(select(Crawl.id).where(Crawl.site_id == site_id, Crawl.org_id == org_id)),
                        AiUsage.issue_id.in_(issue_ids),
                    ),
                )
            )
        ),
        "change_log": _delete_count(
            await db.execute(delete(ChangeLog).where(ChangeLog.site_id == site_id, ChangeLog.org_id == org_id))
        ),
        "page_sources": _delete_count(
            await db.execute(delete(PageSource).where(PageSource.site_id == site_id, PageSource.org_id == org_id))
        ),
        "snippet_events": _delete_count(
            await db.execute(delete(SnippetEvent).where(SnippetEvent.site_id == site_id, SnippetEvent.org_id == org_id))
        ),
        "keyword_rankings": _delete_count(
            await db.execute(delete(KeywordRanking).where(KeywordRanking.site_id == site_id, KeywordRanking.org_id == org_id))
        ),
        "keywords": _delete_count(
            await db.execute(delete(Keyword).where(Keyword.site_id == site_id, Keyword.org_id == org_id))
        ),
        "competitor_page_comparisons": _delete_count(
            await db.execute(delete(CompetitorPageComparison).where(CompetitorPageComparison.site_id == site_id, CompetitorPageComparison.org_id == org_id))
        ),
        "competitors": _delete_count(
            await db.execute(delete(Competitor).where(Competitor.site_id == site_id, Competitor.org_id == org_id))
        ),
        "backlinks": _delete_count(
            await db.execute(delete(Backlink).where(Backlink.site_id == site_id, Backlink.org_id == org_id))
        ),
        "scheduled_reports": _delete_count(
            await db.execute(delete(ScheduledReport).where(ScheduledReport.site_id == site_id, ScheduledReport.org_id == org_id))
        ),
        "content_briefs": _delete_count(
            await db.execute(delete(ContentBrief).where(ContentBrief.site_id == site_id, ContentBrief.org_id == org_id))
        ),
        "site_opportunities": _delete_count(
            await db.execute(delete(SiteOpportunity).where(SiteOpportunity.site_id == site_id, SiteOpportunity.org_id == org_id))
        ),
        "snippet_insights": _delete_count(
            await db.execute(delete(SnippetInsight).where(SnippetInsight.site_id == site_id, SnippetInsight.org_id == org_id))
        ),
        "search_console_inspections": _delete_count(
            await db.execute(delete(SearchConsoleInspection).where(SearchConsoleInspection.site_id == site_id, SearchConsoleInspection.org_id == org_id))
        ),
        "search_console_sitemaps": _delete_count(
            await db.execute(delete(SearchConsoleSitemap).where(SearchConsoleSitemap.site_id == site_id, SearchConsoleSitemap.org_id == org_id))
        ),
        "search_console_query_metrics": _delete_count(
            await db.execute(delete(SearchConsoleQueryMetric).where(SearchConsoleQueryMetric.site_id == site_id, SearchConsoleQueryMetric.org_id == org_id))
        ),
        "search_console_page_metrics": _delete_count(
            await db.execute(delete(SearchConsolePageMetric).where(SearchConsolePageMetric.site_id == site_id, SearchConsolePageMetric.org_id == org_id))
        ),
        "search_console_sync_runs": _delete_count(
            await db.execute(delete(SearchConsoleSyncRun).where(SearchConsoleSyncRun.site_id == site_id, SearchConsoleSyncRun.org_id == org_id))
        ),
        "search_console_connections": _delete_count(
            await db.execute(delete(SearchConsoleConnection).where(SearchConsoleConnection.site_id == site_id, SearchConsoleConnection.org_id == org_id))
        ),
        "analytics_page_metrics": _delete_count(
            await db.execute(delete(AnalyticsPageMetric).where(AnalyticsPageMetric.site_id == site_id, AnalyticsPageMetric.org_id == org_id))
        ),
        "google_analytics_sync_runs": _delete_count(
            await db.execute(delete(GoogleAnalyticsSyncRun).where(GoogleAnalyticsSyncRun.site_id == site_id, GoogleAnalyticsSyncRun.org_id == org_id))
        ),
        "google_analytics_connections": _delete_count(
            await db.execute(delete(GoogleAnalyticsConnection).where(GoogleAnalyticsConnection.site_id == site_id, GoogleAnalyticsConnection.org_id == org_id))
        ),
        "pagespeed_runs": _delete_count(
            await db.execute(delete(PageSpeedRun).where(PageSpeedRun.site_id == site_id, PageSpeedRun.org_id == org_id))
        ),
        "indexnow_submissions": _delete_count(
            await db.execute(delete(IndexNowSubmission).where(IndexNowSubmission.site_id == site_id, IndexNowSubmission.org_id == org_id))
        ),
        "indexnow_keys": _delete_count(
            await db.execute(delete(IndexNowKey).where(IndexNowKey.site_id == site_id, IndexNowKey.org_id == org_id))
        ),
        "report_share_links": _delete_count(
            await db.execute(delete(ReportShareLink).where(ReportShareLink.site_id == site_id, ReportShareLink.org_id == org_id))
        ),
        "fix_proof_snapshots": _delete_count(
            await db.execute(delete(FixProofSnapshot).where(FixProofSnapshot.site_id == site_id, FixProofSnapshot.org_id == org_id))
        ),
        "autopilot_runs": _delete_count(
            await db.execute(delete(AutopilotRun).where(AutopilotRun.site_id == site_id, AutopilotRun.org_id == org_id))
        ),
        "ai_visibility_runs": _delete_count(
            await db.execute(delete(AiVisibilityRun).where(AiVisibilityRun.site_id == site_id, AiVisibilityRun.org_id == org_id))
        ),
        "ai_visibility_prompts": _delete_count(
            await db.execute(delete(AiVisibilityPrompt).where(AiVisibilityPrompt.site_id == site_id, AiVisibilityPrompt.org_id == org_id))
        ),
        "keyword_provider_sync_runs": _delete_count(
            await db.execute(delete(KeywordProviderSyncRun).where(KeywordProviderSyncRun.site_id == site_id, KeywordProviderSyncRun.org_id == org_id))
        ),
        "crawl_log_entries": _delete_count(
            await db.execute(delete(CrawlLogEntry).where(CrawlLogEntry.site_id == site_id, CrawlLogEntry.org_id == org_id))
        ),
        "crawl_log_imports": _delete_count(
            await db.execute(delete(CrawlLogImport).where(CrawlLogImport.site_id == site_id, CrawlLogImport.org_id == org_id))
        ),
        "client_sites": _delete_count(
            await db.execute(delete(ClientSite).where(ClientSite.site_id == site_id, ClientSite.org_id == org_id))
        ),
        "issues": _delete_count(
            await db.execute(delete(Issue).where(Issue.site_id == site_id, Issue.org_id == org_id))
        ),
        "pages": _delete_count(
            await db.execute(delete(Page).where(Page.site_id == site_id, Page.org_id == org_id))
        ),
        "crawls": _delete_count(
            await db.execute(delete(Crawl).where(Crawl.site_id == site_id, Crawl.org_id == org_id))
        ),
        "site": _delete_count(
            await db.execute(delete(Site).where(Site.id == site_id, Site.org_id == org_id))
        ),
    }
    return counts


@router.get("", response_model=SiteListResponse)
async def list_sites(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all sites for the current organization."""
    # Count total
    count_q = select(func.count(Site.id)).where(Site.org_id == auth.org_id)
    total = (await db.execute(count_q)).scalar() or 0

    # Fetch page
    offset = (page - 1) * per_page
    query = (
        select(Site)
        .where(Site.org_id == auth.org_id)
        .order_by(Site.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(query)
    sites = result.scalars().all()

    return SiteListResponse(sites=sites, total=total)


@router.post("", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site(
    data: SiteCreate,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a new site to monitor."""
    # Normalize domain
    domain = data.domain.lower().strip()
    if not domain.startswith(("http://", "https://")):
        domain = f"https://{domain}"

    # Check for duplicate domain in org
    existing = await db.execute(
        select(Site).where(Site.org_id == auth.org_id, Site.domain == domain)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Site {domain} already exists in your organization",
        )

    site = Site(
        org_id=auth.org_id,
        name=data.name,
        domain=domain,
        connection_type=data.connection_type,
        cms_endpoint=data.cms_endpoint,
        github_repo=data.github_repo,
        github_branch=data.github_branch,
        crawl_frequency=data.crawl_frequency,
        crawl_max_pages=data.crawl_max_pages,
        respect_robots_txt=data.respect_robots_txt,
        crawl_delay_ms=data.crawl_delay_ms,
        status="pending",
    )
    db.add(site)
    await db.commit()
    await db.refresh(site)

    return site


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific site by ID."""
    result = await db.execute(
        select(Site).where(Site.id == site_id, Site.org_id == auth.org_id)
    )
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


@router.get("/{site_id}/setup")
async def get_site_setup(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the site setup checklist and readiness state."""
    site = (
        await db.execute(select(Site).where(Site.id == site_id, Site.org_id == auth.org_id))
    ).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    latest_crawl = (
        await db.execute(
            select(Crawl)
            .where(Crawl.site_id == site_id, Crawl.org_id == auth.org_id, Crawl.status == "completed")
            .order_by(Crawl.completed_at.desc().nullslast(), Crawl.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return site_setup_payload(site, latest_crawl)


@router.get("/{site_id}/summary")
async def get_site_summary(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = (
        await db.execute(select(Site).where(Site.id == site_id, Site.org_id == auth.org_id))
    ).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    latest_crawl = (
        await db.execute(
            select(Crawl)
            .where(Crawl.site_id == site_id, Crawl.org_id == auth.org_id, Crawl.status == "completed")
            .order_by(Crawl.completed_at.desc().nullslast(), Crawl.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    latest_crawl_id = latest_crawl.id if latest_crawl else None
    pages_count = 0
    if latest_crawl_id:
        pages_count = int(
            (
                await db.execute(
                    select(func.count(Page.id)).where(Page.crawl_id == latest_crawl_id, Page.site_id == site_id)
                )
            ).scalar()
            or 0
        )

    open_issues = int(
        (
            await db.execute(
                select(func.count(Issue.id)).where(
                    Issue.site_id == site_id,
                    Issue.org_id == auth.org_id,
                    Issue.fix_status.notin_([FIX_STATUS_DEPLOYED, FIX_STATUS_DEPLOYED_AFTER_MERGE, FIX_STATUS_ROLLED_BACK, "applied"]),
                )
            )
        ).scalar()
        or 0
    )
    deployed_fixes = int(
        (
            await db.execute(
                select(func.count(Issue.id)).where(
                    Issue.site_id == site_id,
                    Issue.org_id == auth.org_id,
                    Issue.fix_status.in_([FIX_STATUS_DEPLOYED, FIX_STATUS_DEPLOYED_AFTER_MERGE, "applied"]),
                )
            )
        ).scalar()
        or 0
    )

    severity_rows = (
        await db.execute(
            select(Issue.severity, func.count(Issue.id))
            .where(Issue.site_id == site_id, Issue.org_id == auth.org_id)
            .group_by(Issue.severity)
        )
    ).all()
    setup = site_setup_payload(site, latest_crawl)
    connection = connection_status_payload(site)
    gsc_connection = (
        await db.execute(
            select(SearchConsoleConnection)
            .where(SearchConsoleConnection.site_id == site_id, SearchConsoleConnection.org_id == auth.org_id)
        )
    ).scalar_one_or_none()
    gsc_latest_sync = (
        await db.execute(
            select(SearchConsoleSyncRun)
            .where(SearchConsoleSyncRun.site_id == site_id, SearchConsoleSyncRun.org_id == auth.org_id)
            .order_by(SearchConsoleSyncRun.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    gsc_totals = (
        await db.execute(
            select(
                func.sum(SearchConsolePageMetric.clicks),
                func.sum(SearchConsolePageMetric.impressions),
                func.avg(SearchConsolePageMetric.ctr),
                func.avg(SearchConsolePageMetric.position),
            ).where(SearchConsolePageMetric.site_id == site_id, SearchConsolePageMetric.org_id == auth.org_id)
        )
    ).one()
    analytics_connection = (
        await db.execute(
            select(GoogleAnalyticsConnection)
            .where(GoogleAnalyticsConnection.site_id == site_id, GoogleAnalyticsConnection.org_id == auth.org_id)
        )
    ).scalar_one_or_none()
    analytics_totals = (
        await db.execute(
            select(
                func.sum(AnalyticsPageMetric.sessions),
                func.sum(AnalyticsPageMetric.key_events),
                func.sum(AnalyticsPageMetric.total_revenue),
                func.sum(AnalyticsPageMetric.transactions),
            ).where(AnalyticsPageMetric.site_id == site_id, AnalyticsPageMetric.org_id == auth.org_id)
        )
    ).one()
    pagespeed_totals = (
        await db.execute(
            select(
                func.avg(PageSpeedRun.performance_score),
                func.avg(PageSpeedRun.lcp_ms),
                func.avg(PageSpeedRun.inp_ms),
                func.avg(PageSpeedRun.cls_score),
            ).where(PageSpeedRun.site_id == site_id, PageSpeedRun.org_id == auth.org_id, PageSpeedRun.status == "completed")
        )
    ).one()
    indexnow_key = (
        await db.execute(select(IndexNowKey).where(IndexNowKey.site_id == site_id, IndexNowKey.org_id == auth.org_id))
    ).scalar_one_or_none()

    return {
        "site": SiteResponse.model_validate(site).model_dump(mode="json"),
        "latest_crawl": {
            "id": str(latest_crawl.id),
            "status": latest_crawl.status,
            "seo_score": latest_crawl.seo_score,
            "pages_crawled": latest_crawl.pages_crawled,
            "pages_total": latest_crawl.pages_total,
            "urls_discovered": latest_crawl.urls_discovered or 0,
            "urls_skipped": latest_crawl.urls_skipped or 0,
            "crawl_limit": latest_crawl.crawl_limit,
            "coverage_reason": latest_crawl.coverage_reason,
            "coverage_details": latest_crawl.coverage_details or {},
            "issues_found": latest_crawl.issues_found,
            "completed_at": latest_crawl.completed_at.isoformat() if latest_crawl.completed_at else None,
        }
        if latest_crawl
        else None,
        "metrics": {
            "pages_count": pages_count,
            "open_issues": open_issues,
            "deployed_fixes": deployed_fixes,
            "ownership_verified": bool(site.ownership_verified),
        },
        "issues_by_severity": {
            "critical": next((count for severity, count in severity_rows if severity == "critical"), 0),
            "high": next((count for severity, count in severity_rows if severity == "high"), 0),
            "medium": next((count for severity, count in severity_rows if severity == "medium"), 0),
            "low": next((count for severity, count in severity_rows if severity == "low"), 0),
        },
        "setup": setup,
        "connection": connection,
        "search_console": {
            "connected": bool(gsc_connection),
            "property_url": gsc_connection.property_url if gsc_connection else site.gsc_property_url,
            "last_sync_at": gsc_connection.last_sync_at.isoformat() if gsc_connection and gsc_connection.last_sync_at else None,
            "latest_sync_status": gsc_latest_sync.status if gsc_latest_sync else None,
            "totals": {
                "clicks": float(gsc_totals[0] or 0),
                "impressions": float(gsc_totals[1] or 0),
                "ctr": float(gsc_totals[2] or 0),
                "position": float(gsc_totals[3] or 0),
            },
        },
        "analytics": {
            "connected": bool(analytics_connection),
            "property_id": analytics_connection.property_id if analytics_connection else None,
            "property_name": analytics_connection.property_name if analytics_connection else None,
            "last_sync_at": analytics_connection.last_sync_at.isoformat() if analytics_connection and analytics_connection.last_sync_at else None,
            "totals": {
                "sessions": float(analytics_totals[0] or 0),
                "key_events": float(analytics_totals[1] or 0),
                "total_revenue": float(analytics_totals[2] or 0),
                "transactions": float(analytics_totals[3] or 0),
            },
        },
        "pagespeed": {
            "avg_performance_score": round(float(pagespeed_totals[0]), 1) if pagespeed_totals[0] is not None else None,
            "avg_lcp_ms": round(float(pagespeed_totals[1]), 1) if pagespeed_totals[1] is not None else None,
            "avg_inp_ms": round(float(pagespeed_totals[2]), 1) if pagespeed_totals[2] is not None else None,
            "avg_cls_score": round(float(pagespeed_totals[3]), 4) if pagespeed_totals[3] is not None else None,
        },
        "indexnow": {
            "configured": bool(indexnow_key),
            "verified": bool(indexnow_key and indexnow_key.verified),
            "key_location": indexnow_key.key_location if indexnow_key else None,
        },
        "audit_note": "Raw issue totals can move up or down when crawl coverage changes; use grouped root causes to judge whether the underlying SEO problems actually changed.",
    }


@router.get("/{site_id}/pages")
async def list_site_pages(
    site_id: UUID,
    crawl_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = (
        await db.execute(select(Site).where(Site.id == site_id, Site.org_id == auth.org_id))
    ).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    target_crawl_id = crawl_id
    if not target_crawl_id:
        latest_crawl = (
            await db.execute(
                select(Crawl.id)
                .where(Crawl.site_id == site_id, Crawl.org_id == auth.org_id)
                .order_by(Crawl.completed_at.desc().nullslast(), Crawl.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        target_crawl_id = latest_crawl

    if not target_crawl_id:
        return {"site_id": str(site_id), "crawl_id": None, "pages": [], "total": 0}

    total = int(
        (
            await db.execute(
                select(func.count(Page.id)).where(Page.site_id == site_id, Page.crawl_id == target_crawl_id)
            )
        ).scalar()
        or 0
    )
    rows = (
        await db.execute(
            select(Page)
            .where(Page.site_id == site_id, Page.crawl_id == target_crawl_id)
            .order_by(Page.seo_score.asc().nullslast(), Page.url.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).scalars().all()

    page_ids = [row.id for row in rows]
    issue_counts = {
        page_id: count
        for page_id, count in (
            await db.execute(
                select(Issue.page_id, func.count(Issue.id))
                .where(Issue.page_id.in_(page_ids))
                .group_by(Issue.page_id)
            )
        ).all()
    } if page_ids else {}
    source_rows = (
        await db.execute(
            select(PageSource)
            .where(PageSource.page_id.in_(page_ids))
            .order_by(PageSource.last_synced_at.desc(), PageSource.created_at.desc())
        )
    ).scalars().all() if page_ids else []
    source_map: dict[UUID, PageSource] = {}
    for source in source_rows:
        if source.page_id and source.page_id not in source_map:
            source_map[source.page_id] = source

    return {
        "site_id": str(site_id),
        "crawl_id": str(target_crawl_id),
        "crawl_context": {
            "site_id": str(site_id),
            "crawl_id": str(target_crawl_id),
            "monitoring_mode": connection_status_payload(site)["monitoring_mode"],
        },
        "pages": [
            {
                "id": str(row.id),
                "url": row.url,
                "title": row.title,
                "status_code": row.status_code,
                "seo_score": row.seo_score,
                "word_count": row.word_count,
                "response_time_ms": row.response_time_ms,
                "issue_count": int(issue_counts.get(row.id, 0)),
                "source": {
                    "connection_type": source_map[row.id].connection_type,
                    "source_page_id": source_map[row.id].source_page_id,
                    "source_path": source_map[row.id].source_path,
                    "source_url": source_map[row.id].source_url,
                } if row.id in source_map else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ],
        "total": total,
    }


@router.get("/{site_id}/opportunities")
async def get_site_opportunities(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = (
        await db.execute(select(Site).where(Site.id == site_id, Site.org_id == auth.org_id))
    ).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return await site_opportunities(db, site=site)


@router.post("/{site_id}/verify")
async def start_site_verification(
    site_id: UUID,
    data: dict | None = None,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = (
        await db.execute(select(Site).where(Site.id == site_id, Site.org_id == auth.org_id))
    ).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    method = (data or {}).get("method") or "meta_tag"
    if method not in {"meta_tag", "html_file"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported verification method")

    token = secrets.token_urlsafe(24)
    site.verification_method = method
    site.verification_token = token
    site.verification_requested_at = datetime.now(timezone.utc)
    site.ownership_verified = False
    await db.commit()

    verification_target = site.domain if str(site.domain).startswith("http") else f"https://{site.domain}"
    return {
        "site_id": str(site.id),
        "method": method,
        "token": token,
        "instructions": {
            "meta_tag": f'<meta name="autoseo-site-verification" content="{token}" />',
            "html_file": {
                "filename": f"autoseo-verification-{token}.txt",
                "contents": token,
                "url": f"{verification_target.rstrip('/')}/autoseo-verification-{token}.txt",
            },
        }[method],
    }


@router.post("/{site_id}/verify/check")
async def check_site_verification(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = (
        await db.execute(select(Site).where(Site.id == site_id, Site.org_id == auth.org_id))
    ).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    if not site.verification_token or not site.verification_method:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification has not been started")

    domain = site.domain if str(site.domain).startswith("http") else f"https://{site.domain}"
    if not is_safe_url(domain):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Site domain failed safety validation")

    verified = False
    checked_url = domain
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        if site.verification_method == "meta_tag":
            resp = await client.get(domain)
            checked_url = str(resp.url)
            body = resp.text.lower()
            token = site.verification_token.lower()
            verified = (
                resp.status_code == 200
                and is_safe_url(checked_url)
                and "autoseo-site-verification" in body
                and token in body
            )
        elif site.verification_method == "html_file":
            checked_url = f"{domain.rstrip('/')}/autoseo-verification-{site.verification_token}.txt"
            resp = await client.get(checked_url)
            verified = resp.status_code == 200 and is_safe_url(str(resp.url)) and site.verification_token in resp.text

    if verified:
        site.ownership_verified = True
        site.verified_at = datetime.now(timezone.utc)
        site.status = "active" if site.last_crawled_at else "pending"
        await db.commit()

    return {
        "site_id": str(site.id),
        "verified": verified,
        "method": site.verification_method,
        "checked_url": checked_url,
        "verified_at": site.verified_at.isoformat() if site.verified_at else None,
    }


@router.patch("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: UUID,
    data: SiteUpdate,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update site settings."""
    result = await db.execute(
        select(Site).where(Site.id == site_id, Site.org_id == auth.org_id)
    )
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(site, field, value)

    await db.commit()
    await db.refresh(site)
    return site


@router.delete("/{site_id}")
async def delete_site(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a site and all related data."""
    result = await db.execute(
        select(Site).where(Site.id == site_id, Site.org_id == auth.org_id)
    )
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    active_crawl = await _active_site_crawl(db, site_id, auth.org_id)
    if active_crawl:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "This site still has an active crawl. Cancel it or wait for it to finish before deleting the site.",
                "crawl_id": str(active_crawl.id),
                "crawl_status": active_crawl.status,
            },
        )

    try:
        deleted_counts = await _delete_site_records(db, site_id, auth.org_id)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return {
        "site_id": str(site_id),
        "site_name": site.name,
        "deleted_counts": deleted_counts,
        "message": f"{site.name} was permanently deleted.",
    }
