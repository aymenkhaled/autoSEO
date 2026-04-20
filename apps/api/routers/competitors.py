"""Competitors router — competitor tracking and analysis."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from dependencies import get_db, get_current_user
from schemas.auth import AuthContext
from models.tables import Competitor

router = APIRouter(tags=["competitors"])


class CompetitorCreate(BaseModel):
    site_id: UUID
    domain: str
    name: Optional[str] = None


@router.get("")
async def list_competitors(
    site_id: UUID = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all tracked competitors for a site."""
    result = await db.execute(
        select(Competitor)
        .where(Competitor.site_id == site_id, Competitor.org_id == auth.org_id)
        .order_by(Competitor.created_at.desc())
    )
    competitors = result.scalars().all()
    return {
        "competitors": [
            {
                "id": str(c.id),
                "domain": c.domain,
                "name": c.name,
                "seo_score": c.seo_score,
                "keywords_count": c.keywords_count,
                "backlinks_count": c.backlinks_count,
                "last_analyzed_at": c.last_analyzed_at.isoformat() if c.last_analyzed_at else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in competitors
        ],
        "total": len(competitors),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_competitor(
    data: CompetitorCreate,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a competitor to track."""
    domain = data.domain.lower().strip().rstrip("/")
    if domain.startswith("http://") or domain.startswith("https://"):
        from urllib.parse import urlparse
        domain = urlparse(domain).netloc

    competitor = Competitor(
        org_id=auth.org_id,
        site_id=data.site_id,
        domain=domain,
        name=data.name or domain,
        added_by=auth.user_id,
    )
    db.add(competitor)
    await db.commit()
    await db.refresh(competitor)
    return {
        "id": str(competitor.id),
        "domain": competitor.domain,
        "message": "Competitor added for tracking",
    }


@router.delete("/{competitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_competitor(
    competitor_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a competitor from tracking."""
    result = await db.execute(
        select(Competitor).where(Competitor.id == competitor_id, Competitor.org_id == auth.org_id)
    )
    comp = result.scalar_one_or_none()
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor not found")
    await db.delete(comp)
    await db.commit()
