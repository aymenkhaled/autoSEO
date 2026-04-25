"""PageSpeed Insights and CrUX routes."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dependencies import get_current_user, get_db
from models.tables import PageSpeedRun, Site
from schemas.auth import AuthContext
from services.pagespeed import default_pages_for_site, pagespeed_available, run_pagespeed_check

router = APIRouter(tags=["pagespeed"])
settings = get_settings()


class PageSpeedRunRequest(BaseModel):
    urls: list[str] = Field(default_factory=list)
    strategies: list[str] = Field(default_factory=lambda: ["mobile"])


async def _site(db: AsyncSession, site_id: UUID, org_id: UUID) -> Site:
    site = (
        await db.execute(select(Site).where(Site.id == site_id, Site.org_id == org_id))
    ).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


def _row_payload(row: PageSpeedRun) -> dict:
    return {
        "id": str(row.id),
        "page_url": row.page_url,
        "strategy": row.strategy,
        "status": row.status,
        "performance_score": row.performance_score,
        "accessibility_score": row.accessibility_score,
        "best_practices_score": row.best_practices_score,
        "seo_score": row.seo_score,
        "lcp_ms": row.lcp_ms,
        "inp_ms": row.inp_ms,
        "cls_score": float(row.cls_score or 0) if row.cls_score is not None else None,
        "fcp_ms": row.fcp_ms,
        "ttfb_ms": row.ttfb_ms,
        "total_blocking_time_ms": row.total_blocking_time_ms,
        "speed_index_ms": row.speed_index_ms,
        "opportunities": row.opportunities or [],
        "diagnostics": row.diagnostics or [],
        "crux_metrics": row.crux_metrics or {},
        "error_message": row.error_message,
        "checked_at": row.checked_at.isoformat() if row.checked_at else None,
    }


@router.post("/sites/{site_id}/pagespeed/run")
async def run_pagespeed(
    site_id: UUID,
    data: PageSpeedRunRequest | None = None,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await _site(db, site_id, auth.org_id)
    request = data or PageSpeedRunRequest()
    urls = request.urls or await default_pages_for_site(db, site=site, limit=3)
    strategies = [item for item in request.strategies if item in {"mobile", "desktop"}] or ["mobile"]
    runs = []
    for url in urls[:5]:
        for strategy in strategies[:2]:
            runs.append(await run_pagespeed_check(db, settings, site=site, url=url, strategy=strategy))
    return {
        "site_id": str(site.id),
        "configured": pagespeed_available(settings),
        "runs": [_row_payload(row) for row in runs],
        "message": "PageSpeed checks completed. Failed rows are stored with the provider error so they can be retried.",
    }


@router.get("/sites/{site_id}/pagespeed")
async def list_pagespeed(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await _site(db, site_id, auth.org_id)
    rows = (
        await db.execute(
            select(PageSpeedRun)
            .where(PageSpeedRun.site_id == site.id, PageSpeedRun.org_id == auth.org_id)
            .order_by(PageSpeedRun.checked_at.desc())
            .limit(50)
        )
    ).scalars().all()
    totals = (
        await db.execute(
            select(
                func.avg(PageSpeedRun.performance_score),
                func.avg(PageSpeedRun.lcp_ms),
                func.avg(PageSpeedRun.inp_ms),
                func.avg(PageSpeedRun.cls_score),
            )
            .where(PageSpeedRun.site_id == site.id, PageSpeedRun.org_id == auth.org_id, PageSpeedRun.status == "completed")
        )
    ).one()
    return {
        "site_id": str(site.id),
        "configured": pagespeed_available(settings),
        "readiness": "working",
        "readiness_label": "PageSpeed available",
        "description": "AutoSEO can run Google PageSpeed Insights and CrUX checks for selected pages.",
        "summary": {
            "avg_performance_score": round(float(totals[0]), 1) if totals[0] is not None else None,
            "avg_lcp_ms": round(float(totals[1]), 1) if totals[1] is not None else None,
            "avg_inp_ms": round(float(totals[2]), 1) if totals[2] is not None else None,
            "avg_cls_score": round(float(totals[3]), 4) if totals[3] is not None else None,
        },
        "runs": [_row_payload(row) for row in rows],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
