"""Issues router — list, filter, and view SEO issues."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from typing import Optional

from dependencies import get_db, get_current_user
from schemas.auth import AuthContext
from schemas.issue import IssueResponse, IssueListResponse
from models.tables import Issue

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
        query = query.where(Issue.fix_status == fix_status)
        count_query = count_query.where(Issue.fix_status == fix_status)
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
