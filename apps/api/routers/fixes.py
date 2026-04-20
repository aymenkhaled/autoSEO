"""Fixes router — apply and rollback AI-generated SEO fixes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from datetime import datetime, timezone

from dependencies import get_db, get_current_user
from schemas.auth import AuthContext
from schemas.issue import FixApplyRequest, FixRollbackRequest, FixResponse
from models.tables import Issue, ChangeLog

router = APIRouter(tags=["fixes"])


@router.post("/apply", response_model=FixResponse)
async def apply_fix(
    data: FixApplyRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply an AI-suggested fix to a site via CMS adapter.
    
    In Phase 3+, this will:
    1. Fetch the proposed fix from the issue
    2. Apply it via the appropriate CMS adapter
    3. Re-verify the change was applied
    4. Log to change_log
    """
    result = await db.execute(
        select(Issue).where(Issue.id == data.issue_id, Issue.org_id == auth.org_id)
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    if issue.fix_status == "applied":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Fix already applied",
        )

    if not issue.proposed_fix:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No proposed fix available for this issue",
        )

    # TODO: Phase 3 — actually apply via CMS adapter
    # For now, mark as applied and log
    issue.fix_status = "applied"
    issue.applied_at = datetime.now(timezone.utc)
    issue.applied_by = auth.user_id

    # Audit log
    log_entry = ChangeLog(
        org_id=auth.org_id,
        site_id=issue.site_id,
        issue_id=issue.id,
        action="fix_applied",
        actor_type="user",
        actor_id=auth.user_id,
        old_value=issue.current_value,
        new_value=issue.proposed_fix,
    )
    db.add(log_entry)
    await db.commit()

    return FixResponse(
        issue_id=issue.id,
        status="applied",
        message="Fix applied successfully",
        old_value=issue.current_value,
        new_value=issue.proposed_fix,
    )


@router.post("/rollback", response_model=FixResponse)
async def rollback_fix(
    data: FixRollbackRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rollback a previously applied fix."""
    result = await db.execute(
        select(Issue).where(Issue.id == data.issue_id, Issue.org_id == auth.org_id)
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    if issue.fix_status != "applied":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fix has not been applied yet",
        )

    if not issue.rollback_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No rollback value stored for this fix",
        )

    # TODO: Phase 3 — actually rollback via CMS adapter
    issue.fix_status = "rolled_back"
    issue.rolled_back_at = datetime.now(timezone.utc)

    # Audit log
    log_entry = ChangeLog(
        org_id=auth.org_id,
        site_id=issue.site_id,
        issue_id=issue.id,
        action="fix_rolled_back",
        actor_type="user",
        actor_id=auth.user_id,
        old_value=issue.proposed_fix,
        new_value=issue.rollback_value,
    )
    db.add(log_entry)
    await db.commit()

    return FixResponse(
        issue_id=issue.id,
        status="rolled_back",
        message="Fix rolled back successfully",
        old_value=issue.proposed_fix,
        new_value=issue.rollback_value,
    )
