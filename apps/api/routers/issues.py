"""Issues router — list, filter, and view SEO issues.

Phase 2 additions:
- Missing Feature 6: aggregated view groups identical issue types across pages
  so the UI can show "300 pages missing meta description" as one row instead
  of 300 separate rows.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from typing import Optional

from dependencies import get_db, get_current_user
from schemas.auth import AuthContext
from schemas.issue import IssueResponse, IssueListResponse
from models.tables import Issue, Page
from packages.shared.seo_domain import FIX_STATUS_DEPLOYED, issue_is_auto_fixable, normalize_fix_status

router = APIRouter(tags=["issues"])


@router.get("", response_model=IssueListResponse)
async def list_issues(
    site_id: UUID = Query(None),
    crawl_id: UUID = Query(None),
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    fix_status: Optional[str] = Query(None),
    fix_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List issues with optional filters."""
    query = select(Issue).where(Issue.org_id == auth.org_id)
    count_query = select(func.count(Issue.id)).where(Issue.org_id == auth.org_id)

    # Apply filters
    if site_id:
        query = query.where(Issue.site_id == site_id)
        count_query = count_query.where(Issue.site_id == site_id)
    if crawl_id:
        query = query.where(Issue.crawl_id == crawl_id)
        count_query = count_query.where(Issue.crawl_id == crawl_id)
    if category:
        query = query.where(Issue.category == category)
        count_query = count_query.where(Issue.category == category)
    if severity:
        query = query.where(Issue.severity == severity)
        count_query = count_query.where(Issue.severity == severity)
    if fix_status:
        normalized = normalize_fix_status(fix_status)
        status_values = [FIX_STATUS_DEPLOYED, "applied"] if normalized == FIX_STATUS_DEPLOYED else [normalized]
        query = query.where(Issue.fix_status.in_(status_values))
        count_query = count_query.where(Issue.fix_status.in_(status_values))
    if fix_type:
        query = query.where(Issue.fix_type == fix_type)
        count_query = count_query.where(Issue.fix_type == fix_type)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * per_page
    result = await db.execute(
        query.order_by(Issue.impact_score.desc()).offset(offset).limit(per_page)
    )
    issues = result.scalars().all()

    return IssueListResponse(issues=issues, total=total)


@router.get("/aggregated")
async def list_aggregated_issues(
    site_id: UUID = Query(None),
    crawl_id: UUID = Query(None),
    severity: Optional[str] = Query(None),
    fix_status: Optional[str] = Query("pending"),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Group issues by type so the UI can present them as patterns instead of a flood
    (Missing Feature 6 from the gap analysis).

    Returns one row per issue type with: count, max severity, total impact,
    sample affected URLs, and whether the group can be bulk-fixed.
    """
    conditions = [Issue.org_id == auth.org_id]
    if site_id:
        conditions.append(Issue.site_id == site_id)
    if crawl_id:
        conditions.append(Issue.crawl_id == crawl_id)
    if severity:
        conditions.append(Issue.severity == severity)
    if fix_status:
        normalized = normalize_fix_status(fix_status)
        status_values = [FIX_STATUS_DEPLOYED, "applied"] if normalized == FIX_STATUS_DEPLOYED else [normalized]
        conditions.append(Issue.fix_status.in_(status_values))

    # Aggregate at the DB level to keep this cheap on large sites
    agg = (await db.execute(
        select(
            Issue.type,
            Issue.category,
            func.max(Issue.severity).label("severity"),
            func.count(Issue.id).label("count"),
            func.sum(Issue.impact_score).label("total_impact"),
            func.max(Issue.fix_type).label("fix_type"),
        )
        .where(*conditions)
        .group_by(Issue.type, Issue.category)
        .order_by(func.sum(Issue.impact_score).desc())
    )).all()

    # For each group, fetch up to 5 sample URLs (joined to pages)
    out = []
    for row in agg:
        sample_urls = (await db.execute(
            select(Page.url)
            .join(Issue, Issue.page_id == Page.id)
            .where(*conditions, Issue.type == row.type)
            .limit(5)
        )).scalars().all()

        out.append({
            "type": row.type,
            "category": row.category,
            "severity": row.severity,
            "count": int(row.count or 0),
            "total_impact": int(row.total_impact or 0),
            "fix_type": row.fix_type,
            "can_bulk_fix": issue_is_auto_fixable(row.type),
            "sample_urls": list(sample_urls),
        })

    return {"groups": out, "total_groups": len(out)}


@router.get("/{issue_id}", response_model=IssueResponse)
async def get_issue(
    issue_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific issue with full details."""
    result = await db.execute(
        select(Issue).where(Issue.id == issue_id, Issue.org_id == auth.org_id)
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    return issue
