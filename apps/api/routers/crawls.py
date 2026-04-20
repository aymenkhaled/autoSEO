"""Crawls router — trigger crawls, view status, SSE progress."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
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

    # TODO: In Phase 2, dispatch Celery task here:
    # from workers.tasks.crawl import run_site_crawl
    # run_site_crawl.delay(str(site.id), str(crawl.id))

    return crawl


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
