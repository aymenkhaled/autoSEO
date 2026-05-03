"""Fixes router — apply and rollback AI-generated SEO fixes.

Gap 22 (deferred → done): every apply/rollback writes a `FixVersion` row
giving an authoritative, append-only history independent of the issue's
mutable rollback_value field.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone
import os

from dependencies import get_db, get_current_user
from schemas.auth import AuthContext
from schemas.issue import FixApplyRequest, FixRollbackRequest, FixResponse
from models.tables import Issue, ChangeLog, FixVersion, Site
from packages.shared.seo_domain import (
    FIX_STATUS_APPROVED,
    FIX_STATUS_DEPLOYED,
    FIX_STATUS_DEPLOYED_AFTER_MERGE,
    FIX_STATUS_ROLLED_BACK,
    issue_can_auto_deploy,
    normalize_fix_status,
)

router = APIRouter(tags=["fixes"])


async def _next_version_number(db: AsyncSession, issue_id) -> int:
    res = await db.execute(
        select(func.coalesce(func.max(FixVersion.version_number), 0))
        .where(FixVersion.issue_id == issue_id)
    )
    return int(res.scalar() or 0) + 1


@router.post("/apply", response_model=FixResponse)
async def apply_fix(
    data: FixApplyRequest,
    background: BackgroundTasks,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply an AI-suggested fix to a site via CMS adapter."""
    result = await db.execute(
        select(Issue).where(Issue.id == data.issue_id, Issue.org_id == auth.org_id)
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    current_status = normalize_fix_status(issue.fix_status)
    if current_status in (FIX_STATUS_APPROVED, FIX_STATUS_DEPLOYED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Fix has already been approved",
        )

    if not issue.proposed_fix:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No proposed fix available for this issue",
        )

    site = (await db.execute(select(Site).where(Site.id == issue.site_id))).scalar_one_or_none()
    can_auto_deploy = bool(site and issue_can_auto_deploy(issue.type, site.connection_type))
    if can_auto_deploy and site and not site.ownership_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify site ownership before AutoSEO can deploy or create repository changes. Crawling and manual review still work.",
        )

    # Gap 22: snapshot the pre-fix value into fix_versions BEFORE mutating the issue
    snapshot = FixVersion(
        issue_id=issue.id,
        site_id=issue.site_id,
        org_id=issue.org_id,
        version_number=await _next_version_number(db, issue.id),
        captured_value=issue.current_value,
        applied_value=issue.proposed_fix,
        applied_by=auth.user_id,
        action="apply",
    )
    db.add(snapshot)

    # Preserve rollback target on the issue too (back-compat)
    if not issue.rollback_value:
        issue.rollback_value = issue.current_value

    issue.fix_status = FIX_STATUS_APPROVED
    issue.applied_by = auth.user_id

    log_entry = ChangeLog(
        org_id=auth.org_id,
        site_id=issue.site_id,
        issue_id=issue.id,
        action="fix_approved",
        actor_type="user",
        actor_id=auth.user_id,
        old_value=issue.current_value,
        new_value=issue.proposed_fix,
        extra_metadata={
            "connection_type": site.connection_type if site else None,
            "auto_deploy": can_auto_deploy,
        },
    )
    db.add(log_entry)
    await db.commit()

    # Push to the live CMS via the appropriate adapter (background, fire-and-forget).
    # In dev (no Redis) we run inline; in prod the Celery worker picks it up.
    if can_auto_deploy and site:
        from workers.tasks.fix import apply_ai_fix
        if os.environ.get("REDIS_URL"):
            try:
                apply_ai_fix.delay(str(issue.id), str(site.id))
            except Exception:
                background.add_task(_run_apply_inline, str(issue.id), str(site.id))
        else:
            background.add_task(_run_apply_inline, str(issue.id), str(site.id))

    return FixResponse(
        issue_id=issue.id,
        status=FIX_STATUS_APPROVED,
        message="Fix approved and deployment queued" if can_auto_deploy else "Fix approved; manual follow-up is still required",
        old_value=issue.current_value,
        new_value=issue.proposed_fix,
    )


async def _run_apply_inline(issue_id: str, site_id: str):
    """Run the apply pipeline inline for dev (no Celery worker)."""
    from workers.tasks.fix import _apply_ai_fix_async
    try:
        await _apply_ai_fix_async(issue_id, site_id)
    except Exception:
        # Errors are logged inside the worker; we never crash the request.
        pass


@router.post("/rollback", response_model=FixResponse)
async def rollback_fix(
    data: FixRollbackRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rollback a previously applied fix to its captured pre-fix value."""
    result = await db.execute(
        select(Issue).where(Issue.id == data.issue_id, Issue.org_id == auth.org_id)
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    if normalize_fix_status(issue.fix_status) not in (FIX_STATUS_DEPLOYED, FIX_STATUS_DEPLOYED_AFTER_MERGE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only deployed fixes can be rolled back",
        )

    # Prefer the most recent FixVersion's captured_value over the legacy field
    last_version = (await db.execute(
        select(FixVersion).where(FixVersion.issue_id == issue.id, FixVersion.action == "apply")
        .order_by(FixVersion.version_number.desc())
        .limit(1)
    )).scalar_one_or_none()

    rollback_to = (last_version.captured_value if last_version else None) or issue.rollback_value
    if rollback_to is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No rollback value stored for this fix",
        )

    snapshot = FixVersion(
        issue_id=issue.id,
        site_id=issue.site_id,
        org_id=issue.org_id,
        version_number=await _next_version_number(db, issue.id),
        captured_value=issue.proposed_fix,
        applied_value=rollback_to,
        applied_by=auth.user_id,
        action="rollback",
    )
    db.add(snapshot)

    issue.fix_status = FIX_STATUS_ROLLED_BACK
    issue.rolled_back_at = datetime.now(timezone.utc)

    log_entry = ChangeLog(
        org_id=auth.org_id,
        site_id=issue.site_id,
        issue_id=issue.id,
        action="fix_rolled_back",
        actor_type="user",
        actor_id=auth.user_id,
        old_value=issue.proposed_fix,
        new_value=rollback_to,
        extra_metadata={"rolled_back_from": FIX_STATUS_DEPLOYED},
    )
    db.add(log_entry)
    await db.commit()

    return FixResponse(
        issue_id=issue.id,
        status="rolled_back",
        message="Fix rolled back successfully",
        old_value=issue.proposed_fix,
        new_value=rollback_to,
    )


@router.get("/versions/{issue_id}")
async def list_fix_versions(
    issue_id,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the full version history for an issue (Gap 22)."""
    res = await db.execute(
        select(FixVersion)
        .where(FixVersion.issue_id == issue_id, FixVersion.org_id == auth.org_id)
        .order_by(FixVersion.version_number.asc())
    )
    versions = res.scalars().all()
    return {
        "issue_id": str(issue_id),
        "versions": [
            {
                "id": str(v.id),
                "version_number": v.version_number,
                "action": v.action,
                "captured_value": v.captured_value,
                "applied_value": v.applied_value,
                "applied_by": str(v.applied_by) if v.applied_by else None,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ],
    }
