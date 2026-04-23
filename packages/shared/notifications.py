"""Shared in-app notification helpers."""
from __future__ import annotations

import os
import sys

from sqlalchemy import select

_API_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "apps", "api"))
if _API_ROOT not in sys.path:
    sys.path.insert(0, _API_ROOT)

from models.tables import Notification, NotificationPreference, User


async def notify_org_users(
    db,
    org_id,
    *,
    notification_type: str,
    title: str,
    body: str | None = None,
    data: dict | None = None,
) -> int:
    users = (
        await db.execute(select(User.id).where(User.org_id == org_id))
    ).scalars().all()
    if not users:
        return 0

    prefs = {
        pref.user_id: pref
        for pref in (
            await db.execute(
                select(NotificationPreference).where(NotificationPreference.org_id == org_id)
            )
        ).scalars().all()
    }

    created = 0
    for user_id in users:
        pref = prefs.get(user_id)
        if pref and not pref.in_app_enabled:
            continue
        db.add(
            Notification(
                org_id=org_id,
                user_id=user_id,
                type=notification_type,
                title=title,
                body=body,
                data=data or {},
            )
        )
        created += 1
    return created
