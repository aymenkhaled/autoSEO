"""Proof-driven autopilot orchestration APIs."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dependencies import get_current_user, get_db
from models.tables import AutopilotRun, Site
from schemas.auth import AuthContext
from services.opportunities import site_opportunities
from services.proof_loop import create_proof_snapshot, proof_summary

router = APIRouter(tags=["autopilot"])
settings = get_settings()


class AutopilotRunRequest(BaseModel):
    site_id: UUID | None = None
    run_type: str = "manual"
    create_snapshot: bool = True


async def _sites_for_scope(db: AsyncSession, auth: AuthContext, site_id: UUID | None) -> list[Site]:
    query = select(Site).where(Site.org_id == auth.org_id)
    if site_id:
        query = query.where(Site.id == site_id)
    sites = (await db.execute(query.order_by(Site.created_at.desc()).limit(20))).scalars().all()
    if site_id and not sites:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return list(sites)


def _provider_health() -> dict:
    serp_configured = bool(settings.DATAFORSEO_LOGIN and settings.DATAFORSEO_PASSWORD) or bool(settings.SERPAPI_API_KEY)
    return {
        "gsc": {"configured": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET), "role": "traffic/index data"},
        "ga4": {"configured": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET), "role": "conversion/revenue data"},
        "pagespeed": {"configured": True, "role": "Lighthouse and CrUX opportunities"},
        "github": {"configured": bool(settings.GITHUB_APP_ID and settings.GITHUB_APP_PRIVATE_KEY), "role": "PR-only fix deployment"},
        "resend": {"configured": bool(settings.RESEND_API_KEY), "role": "email digest delivery"},
        "serp_provider": {
            "configured": serp_configured,
            "status": "provider_not_wired",
            "role": "future live rank tracking; CSV import is the working keyword path today",
        },
    }


@router.get("/autopilot/next-actions")
async def next_actions(
    site_id: UUID | None = Query(None),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sites = await _sites_for_scope(db, auth, site_id)
    actions = []
    for site in sites:
        opportunities = await site_opportunities(db, site=site)
        proof = await proof_summary(db, site=site)
        for item in opportunities["opportunities"][:5]:
            actions.append({
                "site_id": str(site.id),
                "site_name": site.name,
                "domain": site.domain,
                "source": item.get("source"),
                "type": item.get("type"),
                "title": item.get("title"),
                "description": item.get("description"),
                "affected_url": item.get("affected_url"),
                "priority_score": item.get("priority_score", 0),
                "impact_label": item.get("impact_label"),
                "proof_status": proof["proof_status"],
                "recommended_next_step": _recommended_next_step(item),
            })
    actions.sort(key=lambda item: item["priority_score"], reverse=True)
    return {
        "actions": actions[:25],
        "total": len(actions),
        "provider_health": _provider_health(),
        "message": "Autopilot ranks next actions by crawler severity, GSC demand, GA4 value, PageSpeed risk, proof state, and fix readiness.",
    }


@router.post("/autopilot/run")
async def run_autopilot(
    data: AutopilotRunRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sites = await _sites_for_scope(db, auth, data.site_id)
    all_actions = []
    snapshots = []
    for site in sites:
        opportunities = await site_opportunities(db, site=site)
        site_actions = [
            {
                "site_id": str(site.id),
                "site_name": site.name,
                "title": item.get("title"),
                "source": item.get("source"),
                "priority_score": item.get("priority_score"),
                "affected_url": item.get("affected_url"),
                "recommended_next_step": _recommended_next_step(item),
            }
            for item in opportunities["opportunities"][:5]
        ]
        all_actions.extend(site_actions)
        if data.create_snapshot:
            snapshot = await create_proof_snapshot(
                db,
                site=site,
                snapshot_type="manual",
                created_by=auth.user_id,
                evidence={"trigger": "autopilot_run", "run_type": data.run_type},
            )
            snapshots.append(str(snapshot.id))

    all_actions.sort(key=lambda item: item.get("priority_score") or 0, reverse=True)
    run = AutopilotRun(
        org_id=auth.org_id,
        site_id=data.site_id,
        status="completed",
        run_type=data.run_type,
        summary=f"Prepared {min(len(all_actions), 25)} prioritized next actions across {len(sites)} site(s).",
        next_actions=all_actions[:25],
        provider_health=_provider_health(),
        created_by=auth.user_id,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return {
        "id": str(run.id),
        "status": run.status,
        "summary": run.summary,
        "next_actions": run.next_actions,
        "proof_snapshot_ids": snapshots,
        "provider_health": run.provider_health,
        "message": "Autopilot run completed. Use the top action as the next weekly focus item.",
    }


@router.get("/sites/{site_id}/digest/preview")
async def site_digest_preview(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = (await db.execute(select(Site).where(Site.id == site_id, Site.org_id == auth.org_id))).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    opportunities = await site_opportunities(db, site=site)
    proof = await proof_summary(db, site=site)
    return {
        "site_id": str(site.id),
        "site_name": site.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "delivery_state": "email_ready" if settings.RESEND_API_KEY else "preview_only",
        "proof": proof,
        "top_actions": opportunities["opportunities"][:8],
        "sections": {
            "changed": _proof_change_line(proof),
            "improved": "Recrawl proof appears in this digest after fixes are merged and crawled again.",
            "broke": "New critical crawler/GSC/PageSpeed findings will be listed as top actions.",
            "waiting": [pr for pr in proof["current"].get("open_prs", [])],
        },
        "message": "This is the weekly digest preview. Email send is available only when RESEND_API_KEY is configured.",
    }


@router.post("/sites/{site_id}/digest/send")
async def send_site_digest(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if auth.email.startswith("api-key:"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Digest email delivery requires a user session with a real recipient email.",
        )
    preview = await site_digest_preview(site_id, auth, db)
    if not settings.RESEND_API_KEY:
        return {
            **preview,
            "sent": False,
            "delivery_state": "preview_only",
            "message": "Digest was not emailed because RESEND_API_KEY is missing. The in-app preview is ready.",
        }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
            json={
                "from": "AutoSEO <digest@autoseo.app>",
                "to": [auth.email],
                "subject": f"AutoSEO weekly digest: {preview['site_name']}",
                "text": _digest_text(preview),
            },
        )
    return {
        **preview,
        "sent": response.status_code in {200, 201, 202},
        "status_code": response.status_code,
        "message": "Digest email sent." if response.status_code in {200, 201, 202} else f"Digest email failed: {response.text[:200]}",
    }


def _recommended_next_step(item: dict) -> str:
    source = item.get("source")
    if source == "crawler" and item.get("issue_type"):
        return "Open the grouped issue, preview the fix workflow, then create a GitHub PR if readiness is green."
    if source == "gsc":
        return "Create a content refresh brief for this page or improve title/meta based on the query intent."
    if source == "ga4":
        return "Prioritize this page before lower-traffic issues because it already affects conversions or revenue."
    if source == "pagespeed":
        return "Run PageSpeed details, fix the largest mobile opportunity, then rerun PageSpeed after deploy."
    if source == "indexnow":
        return "Install the IndexNow key file so post-fix URLs can be submitted after deployment."
    return "Review this opportunity and choose either a GitHub PR, content brief, or manual action."


def _proof_change_line(proof: dict) -> str:
    delta = proof.get("delta")
    if not delta:
        return "No before/after proof pair yet. Create a PR, deploy, recrawl, then compare movement."
    return (
        f"SEO score {delta['seo_score']:+}, open issues {delta['open_issue_count']:+}, "
        f"GSC clicks {delta['gsc_clicks']:+.0f}, revenue ${delta['ga_revenue']:+.2f}."
    )


def _digest_text(preview: dict) -> str:
    lines = [f"AutoSEO digest for {preview['site_name']}", "", preview["sections"]["changed"], ""]
    for index, action in enumerate(preview.get("top_actions", [])[:5], start=1):
        lines.append(f"{index}. {action.get('title')} ({action.get('source')}, score {action.get('priority_score')})")
        lines.append(f"   {action.get('description') or ''}")
    return "\n".join(lines)
