"""Google Analytics 4 revenue and conversion routes."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dependencies import get_current_user, get_db
from models.tables import AnalyticsPageMetric, GoogleAnalyticsConnection, GoogleAnalyticsSyncRun, Site
from schemas.auth import AuthContext
from services.google_analytics import (
    build_connect_url,
    ga_platform_configured,
    parse_state,
    sync_site_google_analytics,
    upsert_connection,
)

router = APIRouter(tags=["google-analytics"])
settings = get_settings()


class AnalyticsCallback(BaseModel):
    code: str
    state: str
    property_id: Optional[str] = None
    property_name: Optional[str] = None


class AnalyticsSyncRequest(BaseModel):
    days: int = 90


async def _site(db: AsyncSession, site_id: UUID, org_id: UUID) -> Site:
    site = (
        await db.execute(select(Site).where(Site.id == site_id, Site.org_id == org_id))
    ).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


async def _connection(db: AsyncSession, site_id: UUID, org_id: UUID) -> GoogleAnalyticsConnection | None:
    return (
        await db.execute(
            select(GoogleAnalyticsConnection).where(
                GoogleAnalyticsConnection.site_id == site_id,
                GoogleAnalyticsConnection.org_id == org_id,
            )
        )
    ).scalar_one_or_none()


@router.get("/google/analytics/connect-url")
async def get_analytics_connect_url(
    site_id: UUID = Query(...),
    property_id: Optional[str] = Query(None),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _site(db, site_id, auth.org_id)
    if not ga_platform_configured(settings):
        return {
            "configured": False,
            "connect_url": None,
            "message": "Google OAuth is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET before connecting GA4.",
        }
    if not property_id:
        return {
            "configured": True,
            "connect_url": None,
            "message": "Enter the numeric GA4 property ID before starting the OAuth flow.",
        }
    try:
        connect_url = build_connect_url(settings, site_id=site_id, org_id=auth.org_id, user_id=auth.user_id, property_id=property_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "configured": True,
        "connect_url": connect_url,
        "scope": "https://www.googleapis.com/auth/analytics.readonly",
        "message": "This grants read-only GA4 access for the selected numeric property ID.",
    }


@router.post("/google/analytics/callback")
async def complete_analytics_post(
    data: AnalyticsCallback,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    state = parse_state(settings, data.state)
    if str(auth.org_id) != state["org_id"] or str(auth.user_id) != state["user_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="OAuth state does not match this user session")
    site = await _site(db, UUID(state["site_id"]), auth.org_id)
    selected_property_id = data.property_id or state.get("property_id")
    if not selected_property_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GA4 property_id is required")
    try:
        connection = await upsert_connection(
            db,
            settings,
            site=site,
            org_id=auth.org_id,
            user_id=auth.user_id,
            code=data.code,
            property_id=selected_property_id,
            property_name=data.property_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"connected": True, "site_id": str(site.id), "property_id": connection.property_id}


@router.get("/google/analytics/callback")
async def complete_analytics_get(
    code: str = Query(...),
    state: str = Query(...),
    property_id: Optional[str] = Query(None),
    property_name: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    parsed = parse_state(settings, state)
    site = await _site(db, UUID(parsed["site_id"]), UUID(parsed["org_id"]))
    selected_property_id = property_id or parsed.get("property_id")
    if not selected_property_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GA4 property_id is required")
    try:
        connection = await upsert_connection(
            db,
            settings,
            site=site,
            org_id=UUID(parsed["org_id"]),
            user_id=UUID(parsed["user_id"]),
            code=code,
            property_id=selected_property_id,
            property_name=property_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "connected": True,
        "site_id": str(site.id),
        "property_id": connection.property_id,
        "message": "Google Analytics connected. You can close this tab and return to AutoSEO.",
    }


@router.get("/sites/{site_id}/analytics/status")
async def analytics_status(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await _site(db, site_id, auth.org_id)
    connection = await _connection(db, site_id, auth.org_id)
    latest_run = (
        await db.execute(
            select(GoogleAnalyticsSyncRun)
            .where(GoogleAnalyticsSyncRun.site_id == site.id, GoogleAnalyticsSyncRun.org_id == auth.org_id)
            .order_by(GoogleAnalyticsSyncRun.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return {
        "site_id": str(site.id),
        "configured": ga_platform_configured(settings),
        "connected": bool(connection),
        "property_id": connection.property_id if connection else None,
        "property_name": connection.property_name if connection else None,
        "scope": "https://www.googleapis.com/auth/analytics.readonly",
        "readiness": "working" if connection else "setup_required",
        "readiness_label": "GA4 connected" if connection else "Connect GA4",
        "description": (
            "AutoSEO can rank opportunities by sessions, key events, transactions, and revenue."
            if connection
            else "Connect GA4 to prove which SEO fixes affect conversions and money."
        ),
        "last_sync_at": connection.last_sync_at.isoformat() if connection and connection.last_sync_at else None,
        "latest_sync": {
            "id": str(latest_run.id),
            "status": latest_run.status,
            "rows_synced": latest_run.rows_synced,
            "error_message": latest_run.error_message,
            "completed_at": latest_run.completed_at.isoformat() if latest_run.completed_at else None,
        } if latest_run else None,
    }


@router.post("/sites/{site_id}/analytics/sync")
async def sync_analytics(
    site_id: UUID,
    data: AnalyticsSyncRequest | None = None,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await _site(db, site_id, auth.org_id)
    connection = await _connection(db, site_id, auth.org_id)
    if not connection:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Google Analytics is not connected for this site.")
    request = data or AnalyticsSyncRequest()
    run = await sync_site_google_analytics(db, settings, site=site, connection=connection, days=request.days)
    return {
        "sync_run_id": str(run.id),
        "status": run.status,
        "rows_synced": run.rows_synced,
        "error_message": run.error_message,
    }


@router.get("/sites/{site_id}/analytics/performance")
async def analytics_performance(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await _site(db, site_id, auth.org_id)
    connection = await _connection(db, site_id, auth.org_id)
    totals = (
        await db.execute(
            select(
                func.sum(AnalyticsPageMetric.sessions),
                func.sum(AnalyticsPageMetric.active_users),
                func.sum(AnalyticsPageMetric.views),
                func.sum(AnalyticsPageMetric.key_events),
                func.sum(AnalyticsPageMetric.total_revenue),
                func.sum(AnalyticsPageMetric.transactions),
                func.avg(AnalyticsPageMetric.engagement_rate),
            )
            .where(AnalyticsPageMetric.site_id == site.id, AnalyticsPageMetric.org_id == auth.org_id)
        )
    ).one()
    top_pages = (
        await db.execute(
            select(AnalyticsPageMetric)
            .where(AnalyticsPageMetric.site_id == site.id, AnalyticsPageMetric.org_id == auth.org_id)
            .order_by(AnalyticsPageMetric.total_revenue.desc(), AnalyticsPageMetric.sessions.desc())
            .limit(12)
        )
    ).scalars().all()
    return {
        "site_id": str(site.id),
        "connected": bool(connection),
        "property_id": connection.property_id if connection else None,
        "synced_at": connection.last_sync_at.isoformat() if connection and connection.last_sync_at else None,
        "totals": {
            "sessions": float(totals[0] or 0),
            "active_users": float(totals[1] or 0),
            "views": float(totals[2] or 0),
            "key_events": float(totals[3] or 0),
            "total_revenue": float(totals[4] or 0),
            "transactions": float(totals[5] or 0),
            "engagement_rate": float(totals[6] or 0),
        },
        "top_pages": [
            {
                "page_url": row.page_url,
                "sessions": float(row.sessions or 0),
                "active_users": float(row.active_users or 0),
                "views": float(row.views or 0),
                "key_events": float(row.key_events or 0),
                "total_revenue": float(row.total_revenue or 0),
                "transactions": float(row.transactions or 0),
                "engagement_rate": float(row.engagement_rate or 0),
            }
            for row in top_pages
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
