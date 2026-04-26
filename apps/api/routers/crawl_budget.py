"""Log-file and crawl-budget APIs."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_current_user, get_db
from models.tables import CrawlLogEntry, CrawlLogImport, Site
from schemas.auth import AuthContext
from services.crawl_budget import crawl_budget_summary, parse_log_lines, summarize_log_entries

router = APIRouter(tags=["crawl-budget"])


class LogImportRequest(BaseModel):
    filename: str | None = None
    raw_log: str = Field(..., min_length=10, max_length=2_000_000)


@router.post("/sites/{site_id}/logs/import", status_code=status.HTTP_201_CREATED)
async def import_logs(
    site_id: UUID,
    data: LogImportRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = (await db.execute(select(Site).where(Site.id == site_id, Site.org_id == auth.org_id))).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    entries, errors = parse_log_lines(data.raw_log, site_domain=site.domain)
    summary = summarize_log_entries(entries, errors)
    import_row = CrawlLogImport(
        org_id=auth.org_id,
        site_id=site.id,
        filename=data.filename,
        status="completed" if entries else "completed_with_no_rows",
        rows_ingested=len(entries),
        summary=summary,
        created_by=auth.user_id,
    )
    db.add(import_row)
    await db.flush()
    db.add_all([
        CrawlLogEntry(
            org_id=auth.org_id,
            site_id=site.id,
            import_id=import_row.id,
            url=entry["url"],
            method=entry["method"],
            status_code=entry["status_code"],
            user_agent=entry["user_agent"],
            bot_family=entry["bot_family"],
            bytes_sent=entry["bytes_sent"],
            requested_at=entry["requested_at"],
        )
        for entry in entries
    ])
    await db.commit()
    return {
        "id": str(import_row.id),
        "rows_ingested": len(entries),
        "summary": summary,
        "message": "Log import completed. Crawl-budget insights now compare bot hits against crawl and GSC data.",
    }


@router.get("/sites/{site_id}/crawl-budget")
async def get_crawl_budget(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = (await db.execute(select(Site).where(Site.id == site_id, Site.org_id == auth.org_id))).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return await crawl_budget_summary(db, site=site)
