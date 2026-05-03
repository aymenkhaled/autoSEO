"""Org dashboard router — overview metrics and recent activity."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_current_user, get_db
from models.tables import Crawl, Issue, Page, Site
from packages.shared.seo_domain import FIX_STATUS_DEPLOYED, FIX_STATUS_DEPLOYED_AFTER_MERGE, FIX_STATUS_ROLLED_BACK
from schemas.auth import AuthContext

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
async def get_org_dashboard(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total_sites = int((await db.execute(select(func.count(Site.id)).where(Site.org_id == auth.org_id))).scalar() or 0)
    open_issues = int(
        (
            await db.execute(
                select(func.count(Issue.id)).where(
                    Issue.org_id == auth.org_id,
                    Issue.fix_status.notin_([FIX_STATUS_DEPLOYED, FIX_STATUS_DEPLOYED_AFTER_MERGE, FIX_STATUS_ROLLED_BACK, "applied", "dismissed"]),
                )
            )
        ).scalar()
        or 0
    )
    deployed_fixes = int(
        (
            await db.execute(
                select(func.count(Issue.id)).where(
                    Issue.org_id == auth.org_id,
                    Issue.fix_status.in_([FIX_STATUS_DEPLOYED, FIX_STATUS_DEPLOYED_AFTER_MERGE, "applied"]),
                )
            )
        ).scalar()
        or 0
    )
    avg_score = (await db.execute(
        select(func.avg(Crawl.seo_score)).where(
            Crawl.org_id == auth.org_id,
            Crawl.status == "completed",
            Crawl.seo_score.isnot(None),
        )
    )).scalar()

    recent_issues = (
        await db.execute(
            select(Issue, Page.url, Site.name)
            .join(Page, Issue.page_id == Page.id, isouter=True)
            .join(Site, Issue.site_id == Site.id)
            .where(Issue.org_id == auth.org_id)
            .order_by(Issue.created_at.desc())
            .limit(8)
        )
    ).all()

    recent_crawls = (
        await db.execute(
            select(Crawl, Site.name)
            .join(Site, Crawl.site_id == Site.id)
            .where(Crawl.org_id == auth.org_id)
            .order_by(Crawl.created_at.desc())
            .limit(8)
        )
    ).all()

    return {
        "metrics": {
            "sites": total_sites,
            "open_issues": open_issues,
            "deployed_fixes": deployed_fixes,
            "avg_seo_score": round(float(avg_score), 1) if avg_score is not None else None,
        },
        "recent_issues": [
            {
                "id": str(issue.id),
                "type": issue.type,
                "severity": issue.severity,
                "site_id": str(issue.site_id),
                "site_name": site_name,
                "page_url": page_url,
                "fix_status": issue.fix_status,
                "created_at": issue.created_at.isoformat() if issue.created_at else None,
            }
            for issue, page_url, site_name in recent_issues
        ],
        "recent_crawls": [
            {
                "id": str(crawl.id),
                "site_id": str(crawl.site_id),
                "site_name": site_name,
                "status": crawl.status,
                "pages_crawled": crawl.pages_crawled,
                "issues_found": crawl.issues_found,
                "seo_score": crawl.seo_score,
                "created_at": crawl.created_at.isoformat() if crawl.created_at else None,
                "completed_at": crawl.completed_at.isoformat() if crawl.completed_at else None,
            }
            for crawl, site_name in recent_crawls
        ],
    }
