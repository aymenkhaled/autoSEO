"""Notifications router — in-app notifications with read/unread state."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from uuid import UUID
from typing import Optional

from dependencies import get_db, get_current_user
from schemas.auth import AuthContext
from models.tables import Notification, NotificationPreference

router = APIRouter(tags=["notifications"])


@router.get("")
async def list_notifications(
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List notifications for the current user."""
    query = select(Notification).where(Notification.user_id == auth.user_id)
    if unread_only:
        query = query.where(Notification.read == False)

    count_q = select(func.count(Notification.id)).where(Notification.user_id == auth.user_id)
    if unread_only:
        count_q = count_q.where(Notification.read == False)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        query.order_by(Notification.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    notifications = result.scalars().all()
    return {
        "notifications": [
            {
                "id": str(n.id),
                "type": n.type,
                "title": n.title,
                "body": n.body,
                "data": n.data,
                "read": n.read,
                "read_at": n.read_at.isoformat() if n.read_at else None,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifications
        ],
        "total": total,
        "unread_count": (await db.execute(
            select(func.count(Notification.id))
            .where(Notification.user_id == auth.user_id, Notification.read == False)
        )).scalar() or 0,
    }


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a single notification as read."""
    from datetime import datetime, timezone
    await db.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == auth.user_id)
        .values(read=True, read_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"success": True}


@router.post("/read-all")
async def mark_all_read(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    await db.execute(
        update(Notification)
        .where(Notification.user_id == auth.user_id, Notification.read == False)
        .values(read=True, read_at=now)
    )
    await db.commit()
    return {"success": True}


@router.get("/preferences")
async def get_preferences(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get notification preferences for the current user."""
    prefs = (await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == auth.user_id)
    )).scalar_one_or_none()

    if not prefs:
        return {
            "email_enabled": True,
            "slack_enabled": False,
            "in_app_enabled": True,
            "slack_webhook_url": None,
            "email_crawl_complete": True,
            "email_new_issues": True,
            "email_fix_applied": True,
            "email_weekly_digest": True,
        }

    return {
        "email_enabled": prefs.email_enabled,
        "slack_enabled": prefs.slack_enabled,
        "in_app_enabled": prefs.in_app_enabled,
        "slack_webhook_url": prefs.slack_webhook_url,
        "email_crawl_complete": prefs.email_crawl_complete,
        "email_new_issues": prefs.email_new_issues,
        "email_fix_applied": prefs.email_fix_applied,
        "email_weekly_digest": prefs.email_weekly_digest,
    }


@router.put("/preferences")
async def update_preferences(
    data: dict,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update notification preferences."""
    prefs = (await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == auth.user_id)
    )).scalar_one_or_none()

    if not prefs:
        prefs = NotificationPreference(user_id=auth.user_id, org_id=auth.org_id)
        db.add(prefs)

    allowed_fields = {
        "email_enabled", "slack_enabled", "in_app_enabled", "slack_webhook_url",
        "email_crawl_complete", "email_new_issues", "email_fix_applied", "email_weekly_digest",
    }
    for field, value in data.items():
        if field in allowed_fields:
            setattr(prefs, field, value)

    await db.commit()
    return {"success": True, "message": "Preferences updated"}
