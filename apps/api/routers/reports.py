"""Scheduled reports and on-demand report generation."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_current_user, get_db
from models.tables import Crawl, Issue, Page, ScheduledReport, Site
from packages.shared.readiness import READINESS_SAVED_ONLY, readiness_payload
from routers.issues import _guidance
from schemas.auth import AuthContext

router = APIRouter(tags=["reports"])


def _report_delivery_state(report: ScheduledReport) -> dict[str, str]:
    return readiness_payload(
        READINESS_SAVED_ONLY,
        label="Saved only",
        description="This schedule is stored, but recurring delivery and PDF/email workers are not wired yet.",
    )


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
                "delivery_state": _report_delivery_state(report)["state"],
                "delivery_state_label": _report_delivery_state(report)["label"],
                "delivery_state_description": _report_delivery_state(report)["description"],
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
    delivery_state = _report_delivery_state(report)
    return {
        "id": str(report.id),
        "message": "Report schedule saved",
        "delivery_state": delivery_state["state"],
        "delivery_state_label": delivery_state["label"],
        "delivery_state_description": delivery_state["description"],
    }


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

    previous_crawl = (
        await db.execute(
            select(Crawl)
            .where(
                Crawl.site_id == data.site_id,
                Crawl.org_id == auth.org_id,
                Crawl.status == "completed",
                Crawl.id != target_crawl.id,
                Crawl.created_at < target_crawl.created_at,
            )
            .order_by(Crawl.completed_at.desc().nullslast(), Crawl.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    severity_rows = (
        await db.execute(
            select(Issue.severity, func.count(Issue.id))
            .where(Issue.crawl_id == target_crawl.id, Issue.org_id == auth.org_id)
            .group_by(Issue.severity)
        )
    ).all()
    groups = (
        await db.execute(
            select(
                Issue.type,
                Issue.category,
                func.max(Issue.severity).label("severity"),
                func.count(Issue.id).label("count"),
                func.sum(Issue.impact_score).label("impact"),
            )
            .where(Issue.crawl_id == target_crawl.id, Issue.org_id == auth.org_id)
            .group_by(Issue.type, Issue.category)
            .order_by(func.sum(Issue.impact_score).desc())
        )
    ).all()

    root_causes = []
    for row in groups:
        examples = (
            await db.execute(
                select(Page.url, Issue.current_value)
                .join(Page, Issue.page_id == Page.id, isouter=True)
                .where(
                    Issue.crawl_id == target_crawl.id,
                    Issue.org_id == auth.org_id,
                    Issue.type == row.type,
                    Issue.category == row.category,
                )
                .order_by(Issue.impact_score.desc(), Issue.created_at.desc())
                .limit(6)
            )
        ).all()
        guidance = _guidance(row.type)
        root_causes.append({
            "type": row.type,
            "title": guidance["title"],
            "summary": guidance["summary"],
            "why_it_matters": guidance["why_it_matters"],
            "recommended_fix": guidance["recommended_fix"],
            "category": row.category,
            "severity": row.severity,
            "affected_count": int(row.count or 0),
            "impact": int(row.impact or 0),
            "examples": [
                {"url": url, "current_value": current_value}
                for url, current_value in examples
            ],
        })

    changed_since_last = None
    if previous_crawl:
        changed_since_last = {
            "previous_crawl_id": str(previous_crawl.id),
            "score_delta": (target_crawl.seo_score or 0) - (previous_crawl.seo_score or 0),
            "issues_delta": (target_crawl.issues_found or 0) - (previous_crawl.issues_found or 0),
            "pages_delta": (target_crawl.pages_crawled or 0) - (previous_crawl.pages_crawled or 0),
        }

    return {
        "site_id": str(site.id),
        "crawl_id": str(target_crawl.id),
        "status": "ready",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "seo_score": target_crawl.seo_score,
            "pages_crawled": target_crawl.pages_crawled,
            "issues_found": target_crawl.issues_found,
            "severity_counts": {severity: int(count) for severity, count in severity_rows},
        },
        "root_causes": root_causes,
        "changed_since_last_crawl": changed_since_last,
        "next_actions": [
            {
                "title": item["title"],
                "action": item["recommended_fix"],
                "affected_count": item["affected_count"],
            }
            for item in root_causes[:5]
        ],
        "export_ready": True,
        "note": "Raw issue totals can change when crawl limits or sampling change; use root-cause groups to judge whether the SEO problems changed.",
        "message": "Report data generated with root causes, affected pages, recommendations, and export-ready sections.",
    }
