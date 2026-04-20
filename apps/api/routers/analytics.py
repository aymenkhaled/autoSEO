"""Analytics router — SEO score history and site health metrics."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from typing import Optional
from datetime import datetime, timedelta, timezone

from dependencies import get_db, get_current_user
from schemas.auth import AuthContext
from models.tables import Crawl, Issue, Site

router = APIRouter(tags=["analytics"])


@router.get("/overview")
async def get_analytics_overview(
    site_id: Optional[UUID] = Query(None),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get high-level analytics for the org or a specific site."""
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    # Sites query
    sites_q = select(func.count(Site.id)).where(Site.org_id == auth.org_id)
    total_sites = (await db.execute(sites_q)).scalar() or 0

    # Crawls in last 30 days
    crawls_q = (
        select(func.count(Crawl.id))
        .where(Crawl.org_id == auth.org_id, Crawl.created_at >= thirty_days_ago)
    )
    total_crawls = (await db.execute(crawls_q)).scalar() or 0

    # Issues breakdown
    issues_q = select(Issue.severity, func.count(Issue.id)).where(
        Issue.org_id == auth.org_id,
        Issue.fix_status != "applied",
    ).group_by(Issue.severity)
    if site_id:
        issues_q = issues_q.where(Issue.site_id == site_id)
    issues_result = await db.execute(issues_q)
    issues_by_severity = {row[0]: row[1] for row in issues_result}

    # Average SEO score from latest crawls
    score_q = select(func.avg(Crawl.seo_score)).where(
        Crawl.org_id == auth.org_id,
        Crawl.status == "completed",
        Crawl.seo_score.isnot(None),
    )
    if site_id:
        score_q = score_q.where(Crawl.site_id == site_id)
    avg_score = (await db.execute(score_q)).scalar()

    return {
        "total_sites": total_sites,
        "total_crawls_30d": total_crawls,
        "avg_seo_score": round(float(avg_score), 1) if avg_score else None,
        "issues_by_severity": {
            "critical": issues_by_severity.get("critical", 0),
            "high": issues_by_severity.get("high", 0),
            "medium": issues_by_severity.get("medium", 0),
            "low": issues_by_severity.get("low", 0),
        },
    }


@router.get("/score-history")
async def get_score_history(
    site_id: UUID = Query(...),
    days: int = Query(30, ge=7, le=365),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get SEO score history for a site over time."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(Crawl.completed_at, Crawl.seo_score, Crawl.pages_crawled, Crawl.issues_found)
        .where(
            Crawl.site_id == site_id,
            Crawl.org_id == auth.org_id,
            Crawl.status == "completed",
            Crawl.completed_at >= since,
            Crawl.seo_score.isnot(None),
        )
        .order_by(Crawl.completed_at)
    )
    rows = result.all()
    return {
        "site_id": str(site_id),
        "days": days,
        "data": [
            {
                "date": row[0].isoformat() if row[0] else None,
                "seo_score": row[1],
                "pages_crawled": row[2],
                "issues_found": row[3],
            }
            for row in rows
        ],
    }


@router.get("/issues-trend")
async def get_issues_trend(
    site_id: Optional[UUID] = Query(None),
    days: int = Query(30, ge=7, le=90),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get issues count by category for trend analysis."""
    result = await db.execute(
        select(Issue.category, Issue.severity, func.count(Issue.id))
        .where(Issue.org_id == auth.org_id)
        .group_by(Issue.category, Issue.severity)
    )
    rows = result.all()
    by_category: dict = {}
    for category, severity, count in rows:
        if category not in by_category:
            by_category[category] = {"total": 0}
        by_category[category][severity] = count
        by_category[category]["total"] += count
    return {"issues_by_category": by_category}
