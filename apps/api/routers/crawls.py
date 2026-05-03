"""Crawls router — trigger crawls, view status, SSE progress."""
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from uuid import UUID
import asyncio
import json

from dependencies import get_db, get_current_user
from schemas.auth import AuthContext
from schemas.crawl import CrawlCreate, CrawlResponse, CrawlListResponse
from models.tables import Crawl, Site, Page
from models.database import AsyncSessionLocal

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
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A crawl is already active for this site",
        )
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


@router.get("/{crawl_id}/diff")
async def crawl_diff(
    crawl_id: UUID,
    compare_to: UUID | None = Query(None, description="Crawl ID to compare against; defaults to the previous crawl of the same site"),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compare two crawls of the same site and report what changed
    (Missing Feature 3 — crawl-to-crawl diff).

    Returns: new pages, removed pages, score-improved, score-declined,
    and pages whose title changed since the previous crawl.
    """
    current = (await db.execute(
        select(Crawl).where(Crawl.id == crawl_id, Crawl.org_id == auth.org_id)
    )).scalar_one_or_none()
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crawl not found")

    if compare_to:
        previous = (await db.execute(
            select(Crawl).where(
                Crawl.id == compare_to,
                Crawl.org_id == auth.org_id,
                Crawl.site_id == current.site_id,
            )
        )).scalar_one_or_none()
    else:
        previous = (await db.execute(
            select(Crawl)
            .where(
                Crawl.site_id == current.site_id,
                Crawl.org_id == auth.org_id,
                Crawl.id != current.id,
                Crawl.status == "completed",
                Crawl.started_at < current.started_at,
            )
            .order_by(Crawl.started_at.desc())
            .limit(1)
        )).scalar_one_or_none()

    if not previous:
        return {
            "current_crawl_id": str(current.id),
            "previous_crawl_id": None,
            "message": "No previous crawl to compare against",
            "new_pages": [], "removed_pages": [],
            "score_improved": [], "score_declined": [],
            "title_changed": [],
        }

    cur_pages = (await db.execute(
        select(Page.url, Page.seo_score, Page.title).where(Page.crawl_id == current.id)
    )).all()
    prev_pages = (await db.execute(
        select(Page.url, Page.seo_score, Page.title).where(Page.crawl_id == previous.id)
    )).all()

    cur_map = {p.url: p for p in cur_pages}
    prev_map = {p.url: p for p in prev_pages}

    new_pages = sorted(set(cur_map) - set(prev_map))
    removed_pages = sorted(set(prev_map) - set(cur_map))

    score_improved, score_declined, title_changed = [], [], []
    for url in set(cur_map) & set(prev_map):
        c, p = cur_map[url], prev_map[url]
        cs, ps = c.seo_score or 0, p.seo_score or 0
        if cs > ps:
            score_improved.append({"url": url, "from": ps, "to": cs, "delta": cs - ps})
        elif cs < ps:
            score_declined.append({"url": url, "from": ps, "to": cs, "delta": cs - ps})
        if (c.title or "") != (p.title or ""):
            title_changed.append({"url": url, "from": p.title, "to": c.title})

    score_improved.sort(key=lambda x: -x["delta"])
    score_declined.sort(key=lambda x: x["delta"])

    return {
        "current_crawl_id": str(current.id),
        "previous_crawl_id": str(previous.id),
        "current_started_at": current.started_at.isoformat() if current.started_at else None,
        "previous_started_at": previous.started_at.isoformat() if previous.started_at else None,
        "summary": {
            "new_pages_count": len(new_pages),
            "removed_pages_count": len(removed_pages),
            "score_improved_count": len(score_improved),
            "score_declined_count": len(score_declined),
            "title_changed_count": len(title_changed),
            "site_score_delta": (current.seo_score or 0) - (previous.seo_score or 0),
        },
        "new_pages": new_pages[:100],
        "removed_pages": removed_pages[:100],
        "score_improved": score_improved[:50],
        "score_declined": score_declined[:50],
        "title_changed": title_changed[:50],
    }


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
                    "urls_discovered": current.urls_discovered or 0,
                    "urls_skipped": current.urls_skipped or 0,
                    "crawl_limit": current.crawl_limit,
                    "coverage_reason": current.coverage_reason,
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

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
