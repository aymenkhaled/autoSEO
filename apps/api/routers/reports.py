"""Scheduled reports and on-demand report generation."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_current_user, get_db
from models.tables import Crawl, ScheduledReport, Site
from schemas.auth import AuthContext

router = APIRouter(tags=["reports"])


class ReportCreate(BaseModel):
    name: str
    site_id: Optional[UUID] = None
    type: str = Field(default="weekly")
    format: str = Field(default="pdf")
    recipients: list[str] = Field(default_factory=list)
    schedule_cron: Optional[str] = None


class ReportGenerateRequest(BaseModel):
    site_id: UUID
    crawl_id: Optional[UUID] = None


@router.get("")
async def list_reports(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(ScheduledReport, Site.name)
            .join(Site, ScheduledReport.site_id == Site.id, isouter=True)
            .where(ScheduledReport.org_id == auth.org_id)
            .order_by(ScheduledReport.created_at.desc())
        )
    ).all()
    return {
        "reports": [
            {
                "id": str(report.id),
                "name": report.name,
                "site_id": str(report.site_id) if report.site_id else None,
                "site_name": site_name,
                "type": report.type,
                "format": report.format,
                "recipients": report.recipients,
                "schedule_cron": report.schedule_cron,
                "last_sent_at": report.last_sent_at.isoformat() if report.last_sent_at else None,
                "created_at": report.created_at.isoformat() if report.created_at else None,
            }
            for report, site_name in rows
        ],
        "total": len(rows),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_report(
    data: ReportCreate,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.site_id:
        site = (
            await db.execute(select(Site).where(Site.id == data.site_id, Site.org_id == auth.org_id))
        ).scalar_one_or_none()
        if not site:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    report = ScheduledReport(
        org_id=auth.org_id,
        site_id=data.site_id,
        name=data.name,
        type=data.type,
        format=data.format,
        recipients=data.recipients,
        schedule_cron=data.schedule_cron,
        created_by=auth.user_id,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return {"id": str(report.id), "message": "Report schedule created"}


@router.post("/generate")
async def generate_report(
    data: ReportGenerateRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = (
        await db.execute(select(Site).where(Site.id == data.site_id, Site.org_id == auth.org_id))
    ).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    target_crawl = None
    if data.crawl_id:
        target_crawl = (
            await db.execute(
                select(Crawl).where(Crawl.id == data.crawl_id, Crawl.site_id == data.site_id, Crawl.org_id == auth.org_id)
            )
        ).scalar_one_or_none()
    else:
        target_crawl = (
            await db.execute(
                select(Crawl)
                .where(Crawl.site_id == data.site_id, Crawl.org_id == auth.org_id, Crawl.status == "completed")
                .order_by(Crawl.completed_at.desc().nullslast(), Crawl.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    if not target_crawl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No crawl available for this report")

    return {
        "site_id": str(site.id),
        "crawl_id": str(target_crawl.id),
        "status": "ready",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "seo_score": target_crawl.seo_score,
            "pages_crawled": target_crawl.pages_crawled,
            "issues_found": target_crawl.issues_found,
        },
        "message": "On-demand report data generated. PDF export can be layered on top of this payload.",
    }
