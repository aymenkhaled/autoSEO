"""Google Search Console read-only monitoring routes."""
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
from models.tables import (
    SearchConsoleConnection,
    SearchConsolePageMetric,
    SearchConsoleQueryMetric,
    SearchConsoleSitemap,
    SearchConsoleSyncRun,
    Site,
)
from schemas.auth import AuthContext
from services.search_console import (
    build_connect_url,
    gsc_platform_configured,
    parse_state,
    sync_site_search_console,
    upsert_connection,
)

router = APIRouter(tags=["search-console"])
settings = get_settings()


class SearchConsoleCallback(BaseModel):
    code: str
    state: str
    property_url: Optional[str] = None


class SearchConsoleSyncRequest(BaseModel):
    days: int = 90
    inspect_limit: int = 10


async def _site(db: AsyncSession, site_id: UUID, org_id: UUID) -> Site:
    site = (
        await db.execute(select(Site).where(Site.id == site_id, Site.org_id == org_id))
    ).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


async def _connection(db: AsyncSession, site_id: UUID, org_id: UUID) -> SearchConsoleConnection | None:
    return (
        await db.execute(
            select(SearchConsoleConnection).where(
                SearchConsoleConnection.site_id == site_id,
                SearchConsoleConnection.org_id == org_id,
            )
        )
    ).scalar_one_or_none()


def _status_payload(site: Site, connection: SearchConsoleConnection | None, latest_run: SearchConsoleSyncRun | None):
    platform_configured = gsc_platform_configured(settings)
    connected = bool(connection)
    return {
        "site_id": str(site.id),
        "configured": platform_configured,
        "connected": connected,
        "property_url": connection.property_url if connection else site.gsc_property_url,
        "scope": "https://www.googleapis.com/auth/webmasters.readonly",
        "readiness": "working" if connected else "setup_required",
        "readiness_label": "Search Console connected" if connected else "Connect Search Console",
        "description": (
            "AutoSEO can sync clicks, impressions, CTR, average position, sitemaps, and sampled URL inspection results."
            if connected
            else "Connect a read-only Google Search Console property to prioritize issues by real Google visibility."
        ),
        "last_sync_at": connection.last_sync_at.isoformat() if connection and connection.last_sync_at else None,
        "latest_sync": {
            "id": str(latest_run.id),
            "status": latest_run.status,
            "pages_synced": latest_run.pages_synced,
            "queries_synced": latest_run.queries_synced,
            "inspections_synced": latest_run.inspections_synced,
            "sitemaps_synced": latest_run.sitemaps_synced,
            "error_message": latest_run.error_message,
            "completed_at": latest_run.completed_at.isoformat() if latest_run.completed_at else None,
        } if latest_run else None,
    }


@router.get("/google/search-console/connect-url")
async def get_connect_url(
    site_id: UUID = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await _site(db, site_id, auth.org_id)
    if not gsc_platform_configured(settings):
        return {
            "configured": False,
            "connect_url": None,
            "message": "Google OAuth is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET before connecting Search Console.",
        }
    return {
        "configured": True,
        "connect_url": build_connect_url(settings, site_id=site.id, org_id=auth.org_id, user_id=auth.user_id),
        "scope": "https://www.googleapis.com/auth/webmasters.readonly",
        "message": "This grants read-only Search Console access for traffic, query, sitemap, and URL inspection data.",
    }


@router.post("/google/search-console/callback")
async def complete_search_console_post(
    data: SearchConsoleCallback,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    state = parse_state(settings, data.state)
    if str(auth.org_id) != state["org_id"] or str(auth.user_id) != state["user_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="OAuth state does not match this user session")
    site = await _site(db, UUID(state["site_id"]), auth.org_id)
    connection = await upsert_connection(
        db,
        settings,
        site=site,
        org_id=auth.org_id,
        user_id=auth.user_id,
        code=data.code,
        property_url=data.property_url,
    )
    return {"connected": True, "site_id": str(site.id), "property_url": connection.property_url}


@router.get("/google/search-console/callback")
async def complete_search_console_get(
    code: str = Query(...),
    state: str = Query(...),
    property_url: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    parsed = parse_state(settings, state)
    site = await _site(db, UUID(parsed["site_id"]), UUID(parsed["org_id"]))
    connection = await upsert_connection(
        db,
        settings,
        site=site,
        org_id=UUID(parsed["org_id"]),
        user_id=UUID(parsed["user_id"]),
        code=code,
        property_url=property_url,
    )
    return {
        "connected": True,
        "site_id": str(site.id),
        "property_url": connection.property_url,
        "message": "Search Console connected. You can close this tab and return to AutoSEO.",
    }


@router.get("/sites/{site_id}/search-console/status")
async def search_console_status(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await _site(db, site_id, auth.org_id)
    connection = await _connection(db, site_id, auth.org_id)
    latest_run = (
        await db.execute(
            select(SearchConsoleSyncRun)
            .where(SearchConsoleSyncRun.site_id == site_id, SearchConsoleSyncRun.org_id == auth.org_id)
            .order_by(SearchConsoleSyncRun.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return _status_payload(site, connection, latest_run)


@router.post("/sites/{site_id}/search-console/sync")
async def sync_search_console(
    site_id: UUID,
    data: SearchConsoleSyncRequest | None = None,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await _site(db, site_id, auth.org_id)
    connection = await _connection(db, site_id, auth.org_id)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Search Console is not connected for this site.",
        )
    request = data or SearchConsoleSyncRequest()
    run = await sync_site_search_console(
        db,
        settings,
        site=site,
        connection=connection,
        days=request.days,
        inspect_limit=request.inspect_limit,
    )
    return {
        "sync_run_id": str(run.id),
        "status": run.status,
        "pages_synced": run.pages_synced,
        "queries_synced": run.queries_synced,
        "inspections_synced": run.inspections_synced,
        "sitemaps_synced": run.sitemaps_synced,
        "error_message": run.error_message,
    }


@router.get("/sites/{site_id}/search-console/performance")
async def search_console_performance(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await _site(db, site_id, auth.org_id)
    connection = await _connection(db, site_id, auth.org_id)
    totals = (
        await db.execute(
            select(
                func.sum(SearchConsolePageMetric.clicks),
                func.sum(SearchConsolePageMetric.impressions),
                func.avg(SearchConsolePageMetric.ctr),
                func.avg(SearchConsolePageMetric.position),
            )
            .where(SearchConsolePageMetric.site_id == site.id, SearchConsolePageMetric.org_id == auth.org_id)
        )
    ).one()
    top_pages = (
        await db.execute(
            select(SearchConsolePageMetric)
            .where(SearchConsolePageMetric.site_id == site.id, SearchConsolePageMetric.org_id == auth.org_id)
            .order_by(SearchConsolePageMetric.impressions.desc())
            .limit(10)
        )
    ).scalars().all()
    top_queries = (
        await db.execute(
            select(SearchConsoleQueryMetric)
            .where(SearchConsoleQueryMetric.site_id == site.id, SearchConsoleQueryMetric.org_id == auth.org_id)
            .order_by(SearchConsoleQueryMetric.impressions.desc())
            .limit(10)
        )
    ).scalars().all()
    sitemaps = (
        await db.execute(
            select(SearchConsoleSitemap)
            .where(SearchConsoleSitemap.site_id == site.id, SearchConsoleSitemap.org_id == auth.org_id)
            .order_by(SearchConsoleSitemap.created_at.desc())
            .limit(10)
        )
    ).scalars().all()
    return {
        "site_id": str(site.id),
        "connected": bool(connection),
        "property_url": connection.property_url if connection else site.gsc_property_url,
        "synced_at": connection.last_sync_at.isoformat() if connection and connection.last_sync_at else None,
        "totals": {
            "clicks": float(totals[0] or 0),
            "impressions": float(totals[1] or 0),
            "ctr": float(totals[2] or 0),
            "position": float(totals[3] or 0),
        },
        "top_pages": [
            {
                "page_url": row.page_url,
                "device": row.device,
                "country": row.country,
                "clicks": float(row.clicks or 0),
                "impressions": float(row.impressions or 0),
                "ctr": float(row.ctr or 0),
                "position": float(row.position or 0),
            }
            for row in top_pages
        ],
        "top_queries": [
            {
                "query": row.query,
                "page_url": row.page_url,
                "device": row.device,
                "country": row.country,
                "clicks": float(row.clicks or 0),
                "impressions": float(row.impressions or 0),
                "ctr": float(row.ctr or 0),
                "position": float(row.position or 0),
            }
            for row in top_queries
        ],
        "sitemaps": [
            {
                "path": row.path,
                "is_pending": row.is_pending,
                "is_sitemaps_index": row.is_sitemaps_index,
                "errors": row.errors,
                "warnings": row.warnings,
                "last_submitted": row.last_submitted,
                "last_downloaded": row.last_downloaded,
            }
            for row in sitemaps
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
