"""Scheduled reports and on-demand report generation."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_current_user, get_db
from models.tables import (
    AnalyticsPageMetric,
    Crawl,
    GoogleAnalyticsConnection,
    IndexNowKey,
    Issue,
    Page,
    PageSpeedRun,
    ReportShareLink,
    ScheduledReport,
    SearchConsoleConnection,
    SearchConsolePageMetric,
    Site,
)
from packages.shared.readiness import READINESS_SAVED_ONLY, readiness_payload
from packages.shared.seo_domain import FIX_STATUS_GITHUB_PR_CREATED
from routers.issues import _guidance
from schemas.auth import AuthContext
from services.opportunities import site_opportunities

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


class ReportShareRequest(BaseModel):
    site_id: UUID
    title: str = "SEO action report"
    expires_in_days: int = Field(default=14, ge=1, le=90)


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

    gsc_connection = (
        await db.execute(
            select(SearchConsoleConnection)
            .where(SearchConsoleConnection.site_id == site.id, SearchConsoleConnection.org_id == auth.org_id)
        )
    ).scalar_one_or_none()
    gsc_totals = (
        await db.execute(
            select(
                func.sum(SearchConsolePageMetric.clicks),
                func.sum(SearchConsolePageMetric.impressions),
                func.avg(SearchConsolePageMetric.ctr),
                func.avg(SearchConsolePageMetric.position),
            ).where(SearchConsolePageMetric.site_id == site.id, SearchConsolePageMetric.org_id == auth.org_id)
        )
    ).one()
    ga_connection = (
        await db.execute(
            select(GoogleAnalyticsConnection)
            .where(GoogleAnalyticsConnection.site_id == site.id, GoogleAnalyticsConnection.org_id == auth.org_id)
        )
    ).scalar_one_or_none()
    ga_totals = (
        await db.execute(
            select(
                func.sum(AnalyticsPageMetric.sessions),
                func.sum(AnalyticsPageMetric.key_events),
                func.sum(AnalyticsPageMetric.total_revenue),
                func.sum(AnalyticsPageMetric.transactions),
            ).where(AnalyticsPageMetric.site_id == site.id, AnalyticsPageMetric.org_id == auth.org_id)
        )
    ).one()
    pagespeed_totals = (
        await db.execute(
            select(
                func.avg(PageSpeedRun.performance_score),
                func.avg(PageSpeedRun.lcp_ms),
                func.avg(PageSpeedRun.inp_ms),
                func.avg(PageSpeedRun.cls_score),
            ).where(PageSpeedRun.site_id == site.id, PageSpeedRun.org_id == auth.org_id, PageSpeedRun.status == "completed")
        )
    ).one()
    latest_pagespeed = (
        await db.execute(
            select(PageSpeedRun)
            .where(PageSpeedRun.site_id == site.id, PageSpeedRun.org_id == auth.org_id)
            .order_by(PageSpeedRun.checked_at.desc())
            .limit(5)
        )
    ).scalars().all()
    indexnow_key = (
        await db.execute(select(IndexNowKey).where(IndexNowKey.site_id == site.id, IndexNowKey.org_id == auth.org_id))
    ).scalar_one_or_none()
    open_prs = int(
        (
            await db.execute(
                select(func.count(Issue.id)).where(
                    Issue.site_id == site.id,
                    Issue.org_id == auth.org_id,
                    Issue.fix_status == FIX_STATUS_GITHUB_PR_CREATED,
                )
            )
        ).scalar()
        or 0
    )
    opportunities = await site_opportunities(db, site=site)

    return {
        "site_id": str(site.id),
        "crawl_id": str(target_crawl.id),
        "status": "ready",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "seo_score": target_crawl.seo_score,
            "pages_crawled": target_crawl.pages_crawled,
            "pages_total": target_crawl.pages_total,
            "urls_discovered": target_crawl.urls_discovered or 0,
            "urls_skipped": target_crawl.urls_skipped or 0,
            "crawl_limit": target_crawl.crawl_limit,
            "coverage_reason": target_crawl.coverage_reason,
            "issues_found": target_crawl.issues_found,
            "severity_counts": {severity: int(count) for severity, count in severity_rows},
        },
        "root_causes": root_causes,
        "search_console": {
            "connected": bool(gsc_connection),
            "property_url": gsc_connection.property_url if gsc_connection else site.gsc_property_url,
            "last_sync_at": gsc_connection.last_sync_at.isoformat() if gsc_connection and gsc_connection.last_sync_at else None,
            "totals": {
                "clicks": float(gsc_totals[0] or 0),
                "impressions": float(gsc_totals[1] or 0),
                "ctr": float(gsc_totals[2] or 0),
                "position": float(gsc_totals[3] or 0),
            },
        },
        "analytics": {
            "connected": bool(ga_connection),
            "property_id": ga_connection.property_id if ga_connection else None,
            "last_sync_at": ga_connection.last_sync_at.isoformat() if ga_connection and ga_connection.last_sync_at else None,
            "totals": {
                "sessions": float(ga_totals[0] or 0),
                "key_events": float(ga_totals[1] or 0),
                "total_revenue": float(ga_totals[2] or 0),
                "transactions": float(ga_totals[3] or 0),
            },
        },
        "pagespeed": {
            "summary": {
                "avg_performance_score": round(float(pagespeed_totals[0]), 1) if pagespeed_totals[0] is not None else None,
                "avg_lcp_ms": round(float(pagespeed_totals[1]), 1) if pagespeed_totals[1] is not None else None,
                "avg_inp_ms": round(float(pagespeed_totals[2]), 1) if pagespeed_totals[2] is not None else None,
                "avg_cls_score": round(float(pagespeed_totals[3]), 4) if pagespeed_totals[3] is not None else None,
            },
            "latest_runs": [
                {
                    "page_url": row.page_url,
                    "strategy": row.strategy,
                    "status": row.status,
                    "performance_score": row.performance_score,
                    "lcp_ms": row.lcp_ms,
                    "inp_ms": row.inp_ms,
                    "cls_score": float(row.cls_score or 0) if row.cls_score is not None else None,
                    "checked_at": row.checked_at.isoformat() if row.checked_at else None,
                }
                for row in latest_pagespeed
            ],
        },
        "indexnow": {
            "configured": bool(indexnow_key),
            "verified": bool(indexnow_key and indexnow_key.verified),
            "key_location": indexnow_key.key_location if indexnow_key else None,
        },
        "github_fix_status": {
            "open_pr_issue_count": open_prs,
            "message": "GitHub PR-created issues remain open until a deploy and recrawl proves the root cause disappeared.",
        },
        "top_opportunities": opportunities["opportunities"][:8],
        "changed_since_last_crawl": changed_since_last,
        "next_actions": [
            {
                "title": item.get("title"),
                "action": item.get("description") or item.get("recommended_fix"),
                "priority_score": item.get("priority_score"),
                "source": item.get("source"),
            }
            for item in opportunities["opportunities"][:5]
        ],
        "export_ready": True,
        "note": "Raw issue totals can change when crawl limits or sampling change; use root-cause groups to judge whether the SEO problems changed.",
        "message": "Report data generated with root causes, affected pages, recommendations, and export-ready sections.",
    }


@router.get("/digest/preview")
async def digest_preview(
    site_id: Optional[UUID] = None,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sites_query = select(Site).where(Site.org_id == auth.org_id)
    if site_id:
        sites_query = sites_query.where(Site.id == site_id)
    sites = (await db.execute(sites_query.order_by(Site.created_at.desc()).limit(10))).scalars().all()

    items = []
    for site in sites:
        latest_crawl = (
            await db.execute(
                select(Crawl)
                .where(Crawl.site_id == site.id, Crawl.org_id == auth.org_id, Crawl.status == "completed")
                .order_by(Crawl.completed_at.desc().nullslast(), Crawl.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        opportunities = await site_opportunities(db, site=site)
        items.append({
            "site_id": str(site.id),
            "site_name": site.name,
            "domain": site.domain,
            "seo_score": latest_crawl.seo_score if latest_crawl else None,
            "issues_found": latest_crawl.issues_found if latest_crawl else 0,
            "pages_crawled": latest_crawl.pages_crawled if latest_crawl else 0,
            "top_opportunities": opportunities["opportunities"][:5],
            "next_action": opportunities["opportunities"][0] if opportunities["opportunities"] else None,
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "delivery_state": "preview_only",
        "delivery_state_label": "Preview only",
        "summary": {
            "sites": len(items),
            "open_opportunities": sum(len(item["top_opportunities"]) for item in items),
        },
        "sites": items,
        "message": "Digest preview is available in-app. Email delivery becomes active when RESEND_API_KEY and the worker schedule are configured.",
    }


@router.post("/share-link")
async def create_report_share_link(
    data: ReportShareRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = (
        await db.execute(select(Site).where(Site.id == data.site_id, Site.org_id == auth.org_id))
    ).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    latest_crawl = (
        await db.execute(
            select(Crawl)
            .where(Crawl.site_id == site.id, Crawl.org_id == auth.org_id, Crawl.status == "completed")
            .order_by(Crawl.completed_at.desc().nullslast(), Crawl.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    opportunities = await site_opportunities(db, site=site)
    snapshot = {
        "site": {"id": str(site.id), "name": site.name, "domain": site.domain},
        "latest_crawl": {
            "seo_score": latest_crawl.seo_score,
            "pages_crawled": latest_crawl.pages_crawled,
            "issues_found": latest_crawl.issues_found,
            "completed_at": latest_crawl.completed_at.isoformat() if latest_crawl.completed_at else None,
        } if latest_crawl else None,
        "top_opportunities": opportunities["opportunities"][:10],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    token = secrets.token_urlsafe(32)
    link = ReportShareLink(
        org_id=auth.org_id,
        site_id=site.id,
        token=token,
        title=data.title,
        snapshot=snapshot,
        expires_at=datetime.now(timezone.utc) + timedelta(days=data.expires_in_days),
        created_by=auth.user_id,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return {
        "id": str(link.id),
        "token": link.token,
        "share_url": f"/api/v1/reports/shared/{link.token}",
        "expires_at": link.expires_at.isoformat() if link.expires_at else None,
        "message": "Read-only report share link created. It exposes only the stored report snapshot, not credentials or live API access.",
    }


@router.get("/shared/{token}")
async def read_report_share_link(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    link = (
        await db.execute(select(ReportShareLink).where(ReportShareLink.token == token))
    ).scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report link not found")
    if link.expires_at and link.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Report link expired")
    return {
        "title": link.title,
        "snapshot": link.snapshot,
        "created_at": link.created_at.isoformat() if link.created_at else None,
        "expires_at": link.expires_at.isoformat() if link.expires_at else None,
        "read_only": True,
    }
