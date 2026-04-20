"""Change log router — audit trail of all applied fixes."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from typing import Optional

from dependencies import get_db, get_current_user
from schemas.auth import AuthContext
from models.tables import ChangeLog

router = APIRouter(tags=["change-log"])


@router.get("")
async def list_change_log(
    site_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all change log entries (append-only audit trail)."""
    query = select(ChangeLog).where(ChangeLog.org_id == auth.org_id)
    count_q = select(func.count(ChangeLog.id)).where(ChangeLog.org_id == auth.org_id)

    if site_id:
        query = query.where(ChangeLog.site_id == site_id)
        count_q = count_q.where(ChangeLog.site_id == site_id)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        query.order_by(ChangeLog.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    entries = result.scalars().all()

    return {
        "entries": [
            {
                "id": str(e.id),
                "site_id": str(e.site_id),
                "issue_id": str(e.issue_id) if e.issue_id else None,
                "action": e.action,
                "actor_type": e.actor_type,
                "actor_id": str(e.actor_id) if e.actor_id else None,
                "old_value": e.old_value,
                "new_value": e.new_value,
                "metadata": e.metadata,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ],
        "total": total,
    }
