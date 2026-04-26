"""Content refresh brief APIs."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_current_user, get_db
from models.tables import ChangeLog, ContentBrief, Site
from schemas.auth import AuthContext
from services.content_briefs import build_content_brief_payload, serialize_content_brief
from services.github_connection import github_adapter_for_site

router = APIRouter(tags=["content-briefs"])


class ContentBriefCreateRequest(BaseModel):
    site_id: UUID
    page_url: str = Field(..., min_length=8)
    target_keyword: str | None = None
    title: str | None = None


@router.get("/content-briefs")
async def list_content_briefs(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = (await db.execute(select(Site).where(Site.id == site_id, Site.org_id == auth.org_id))).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    rows = (
        await db.execute(
            select(ContentBrief)
            .where(ContentBrief.site_id == site.id, ContentBrief.org_id == auth.org_id)
            .order_by(ContentBrief.created_at.desc())
            .limit(50)
        )
    ).scalars().all()
    return {"briefs": [serialize_content_brief(row) for row in rows], "total": len(rows)}


@router.post("/content-briefs", status_code=status.HTTP_201_CREATED)
async def create_content_brief(
    data: ContentBriefCreateRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = (await db.execute(select(Site).where(Site.id == data.site_id, Site.org_id == auth.org_id))).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    payload = await build_content_brief_payload(
        db,
        site=site,
        page_url=data.page_url,
        target_keyword=data.target_keyword,
        title=data.title,
    )
    row = ContentBrief(
        org_id=auth.org_id,
        site_id=site.id,
        page_url=data.page_url,
        target_keyword=data.target_keyword,
        title=payload["title"],
        brief=payload,
        created_by=auth.user_id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {**serialize_content_brief(row), "message": "Content refresh brief created from crawl, GSC, and GA4 signals."}


@router.post("/content-briefs/{brief_id}/github-pr")
async def create_content_brief_pr(
    brief_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    brief = (
        await db.execute(select(ContentBrief).where(ContentBrief.id == brief_id, ContentBrief.org_id == auth.org_id))
    ).scalar_one_or_none()
    if not brief:
        raise HTTPException(status_code=404, detail="Content brief not found")
    site = (await db.execute(select(Site).where(Site.id == brief.site_id, Site.org_id == auth.org_id))).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    if not site.ownership_verified:
        raise HTTPException(status_code=403, detail="Verify site ownership before AutoSEO creates content PRs.")

    adapter, creds = await github_adapter_for_site(str(auth.org_id), site)
    steps = list((brief.brief or {}).get("github_pr_steps") or [])
    result = await adapter.create_static_fix_pr(
        issue_type="content_refresh",
        title=brief.title,
        site_domain=site.domain,
        affected_urls=[brief.page_url],
        manual_steps=steps,
        project_root=creds.get("project_root") or "",
        build_command=creds.get("build_command"),
        package_manager=creds.get("package_manager"),
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)

    brief.status = "github_pr_plan_created"
    brief.github_pr_url = result.get("pr_url")
    brief.github_branch = result.get("branch")
    brief.updated_at = datetime.now(timezone.utc)
    db.add(
        ChangeLog(
            org_id=auth.org_id,
            site_id=site.id,
            action="content_brief_pr_created",
            actor_type="user",
            actor_id=auth.user_id,
            new_value=result.get("pr_url"),
            extra_metadata={"brief_id": str(brief.id), "page_url": brief.page_url, "files_changed": result.get("files_changed", [])},
        )
    )
    await db.commit()
    return {
        **serialize_content_brief(brief),
        "github": result,
        "message": "GitHub PR plan created. This is a reviewable content-refresh plan, not an automatic live content edit.",
    }
