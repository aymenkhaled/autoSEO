"""AI answer-readiness APIs."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_current_user, get_db
from models.tables import AiVisibilityRun, Site
from schemas.auth import AuthContext
from services.ai_visibility import build_ai_visibility_run, serialize_ai_visibility_run

router = APIRouter(tags=["ai-visibility"])


class AiVisibilityRunRequest(BaseModel):
    prompt: str = Field(..., min_length=5, max_length=500)
    target_entity: str | None = None
    competitor_domains: list[str] = Field(default_factory=list, max_length=8)


@router.get("/sites/{site_id}/ai-visibility")
async def list_ai_visibility_runs(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = (await db.execute(select(Site).where(Site.id == site_id, Site.org_id == auth.org_id))).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    runs = (
        await db.execute(
            select(AiVisibilityRun)
            .where(AiVisibilityRun.site_id == site.id, AiVisibilityRun.org_id == auth.org_id)
            .order_by(AiVisibilityRun.created_at.desc())
            .limit(20)
        )
    ).scalars().all()
    return {
        "site_id": str(site.id),
        "runs": [serialize_ai_visibility_run(run) for run in runs],
        "total": len(runs),
        "readiness": "readiness_scoring_only",
        "label": "AI answer-readiness scoring",
        "message": "This checks whether crawled pages are structured for AI/search answers. It does not yet query ChatGPT, Perplexity, Gemini, or Google AI Overviews.",
    }


@router.post("/sites/{site_id}/ai-visibility/run")
async def run_ai_visibility(
    site_id: UUID,
    data: AiVisibilityRunRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = (await db.execute(select(Site).where(Site.id == site_id, Site.org_id == auth.org_id))).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    run = await build_ai_visibility_run(
        db,
        site=site,
        prompt=data.prompt,
        target_entity=data.target_entity,
        competitor_domains=data.competitor_domains,
        created_by=auth.user_id,
    )
    await db.commit()
    await db.refresh(run)
    return {
        **serialize_ai_visibility_run(run),
        "label": "AI answer-readiness scoring",
        "message": "AI readiness check completed from crawled metadata, content structure, schema, and SEO blockers. Live AI-answer provider checks are not wired yet.",
    }
