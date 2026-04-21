"""Crawls router — trigger crawls, view status, SSE progress."""
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
import asyncio
import json

from dependencies import get_db, get_current_user
from schemas.auth import AuthContext
from schemas.crawl import CrawlCreate, CrawlResponse, CrawlListResponse
from models.tables import Crawl, Site

router = APIRouter(tags=["crawls"])


@router.post("", response_model=CrawlResponse, status_code=status.HTTP_201_CREATED)
async def trigger_crawl(
    data: CrawlCreate,
    background_tasks: BackgroundTasks,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a new crawl for a site."""
    # Verify site belongs to org
    site_result = await db.execute(
        select(Site).where(Site.id == data.site_id, Site.org_id == auth.org_id)
    )
    site = site_result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    # Check no active crawl
    active_crawl = await db.execute(
        select(Crawl).where(
            Crawl.site_id == data.site_id,
            Crawl.status.in_(["queued", "running"]),
        )
    )
    if active_crawl.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A crawl is already running for this site",
        )

    crawl = Crawl(
        site_id=data.site_id,
        org_id=auth.org_id,
        status="queued",
        trigger=data.trigger,
    )
    db.add(crawl)
    await db.commit()
    await db.refresh(crawl)

    # Dispatch the crawl: prefer Celery (production) but fall back to in-process
    # background task when no Redis broker is configured (dev / single-server).
    import sys, pathlib, logging
    log = logging.getLogger("autoseo.dispatch")
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
    site_id_str = str(site.id)
    crawl_id_str = str(crawl.id)
    try:
        if os.environ.get("REDIS_URL"):
            from workers.tasks.crawl import run_site_crawl
            run_site_crawl.delay(site_id_str, crawl_id_str)
            log.info("crawl_dispatched_celery crawl_id=%s", crawl_id_str)
        else:
            from workers.tasks.crawl import _async_crawl
            background_tasks.add_task(_async_crawl, site_id_str, crawl_id_str)
            log.info("crawl_dispatched_background crawl_id=%s", crawl_id_str)
    except Exception as e:
        # Mark crawl as failed so the user gets feedback instead of an eternal "queued"
        log.exception("crawl_dispatch_failed crawl_id=%s err=%s", crawl_id_str, e)
        crawl.status = "failed"
        crawl.error_message = f"Dispatch failed: {e}"
        await db.commit()
        await db.refresh(crawl)

    return crawl


@router.delete("/{crawl_id}", status_code=status.HTTP_202_ACCEPTED)
async def cancel_crawl(
    crawl_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Request cancellation of a running crawl.

    Sets the crawl status to 'cancelling' — the worker checks this between batches
    and stops gracefully (Gap 4 from Phase 2 gap analysis).
    """
    result = await db.execute(
        select(Crawl).where(Crawl.id == crawl_id, Crawl.org_id == auth.org_id)
    )
    crawl = result.scalar_one_or_none()
    if not crawl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crawl not found")
    if crawl.status not in ("queued", "running"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel crawl with status '{crawl.status}'",
        )
    crawl.status = "cancelling"
    await db.commit()
    return {"crawl_id": str(crawl_id), "status": "cancelling"}


@router.get("", response_model=CrawlListResponse)
async def list_crawls(
    site_id: UUID = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List crawls for the organization, optionally filtered by site."""
    query = select(Crawl).where(Crawl.org_id == auth.org_id)
    count_query = select(func.count(Crawl.id)).where(Crawl.org_id == auth.org_id)

    if site_id:
        query = query.where(Crawl.site_id == site_id)
        count_query = count_query.where(Crawl.site_id == site_id)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * per_page
    result = await db.execute(
        query.order_by(Crawl.created_at.desc()).offset(offset).limit(per_page)
    )
    crawls = result.scalars().all()

    return CrawlListResponse(crawls=crawls, total=total)


@router.get("/{crawl_id}", response_model=CrawlResponse)
async def get_crawl(
    crawl_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get crawl details."""
    result = await db.execute(
        select(Crawl).where(Crawl.id == crawl_id, Crawl.org_id == auth.org_id)
    )
    crawl = result.scalar_one_or_none()
    if not crawl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crawl not found")
    return crawl


@router.get("/{crawl_id}/progress")
async def crawl_progress_sse(
    crawl_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SSE endpoint for real-time crawl progress updates."""
    # Verify crawl belongs to org
    result = await db.execute(
        select(Crawl).where(Crawl.id == crawl_id, Crawl.org_id == auth.org_id)
    )
    crawl = result.scalar_one_or_none()
    if not crawl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crawl not found")

    async def event_generator():
        """Poll crawl status and stream updates."""
        while True:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Crawl).where(Crawl.id == crawl_id)
                )
                current = result.scalar_one_or_none()
                if not current:
                    break

                progress = {
                    "crawl_id": str(current.id),
                    "status": current.status,
                    "pages_crawled": current.pages_crawled,
                    "pages_total": current.pages_total,
                    "percentage": (
                        round(current.pages_crawled / current.pages_total * 100, 1)
                        if current.pages_total and current.pages_total > 0
                        else 0
                    ),
                }

                yield f"data: {json.dumps(progress)}\n\n"

                if current.status in ("completed", "failed"):
                    break

            await asyncio.sleep(2)

    from models.database import AsyncSessionLocal
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
