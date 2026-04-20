"""Keywords router — keyword tracking and ranking history."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from dependencies import get_db, get_current_user
from schemas.auth import AuthContext
from models.tables import Keyword, KeywordRanking

router = APIRouter(tags=["keywords"])


class KeywordCreate(BaseModel):
    site_id: UUID
    keyword: str
    target_url: Optional[str] = None
    intent: str = "informational"
    priority: int = 1


class KeywordResponse(BaseModel):
    id: UUID
    site_id: UUID
    keyword: str
    target_url: Optional[str]
    intent: str
    priority: int
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("")
async def list_keywords(
    site_id: UUID = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all tracked keywords for a site."""
    result = await db.execute(
        select(Keyword)
        .where(Keyword.site_id == site_id, Keyword.org_id == auth.org_id)
        .order_by(Keyword.priority.desc(), Keyword.created_at.desc())
    )
    keywords = result.scalars().all()

    # Get latest rankings for each keyword
    kw_list = []
    for kw in keywords:
        latest_ranking = (await db.execute(
            select(KeywordRanking)
            .where(KeywordRanking.keyword_id == kw.id)
            .order_by(KeywordRanking.checked_at.desc())
            .limit(1)
        )).scalar_one_or_none()

        kw_list.append({
            "id": str(kw.id),
            "keyword": kw.keyword,
            "target_url": kw.target_url,
            "intent": kw.intent,
            "priority": kw.priority,
            "created_at": kw.created_at.isoformat() if kw.created_at else None,
            "latest_ranking": {
                "position": latest_ranking.position,
                "previous_position": latest_ranking.previous_position,
                "search_volume": latest_ranking.search_volume,
                "url": latest_ranking.url,
                "checked_at": latest_ranking.checked_at.isoformat() if latest_ranking.checked_at else None,
            } if latest_ranking else None,
        })
    return {"keywords": kw_list, "total": len(kw_list)}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_keyword(
    data: KeywordCreate,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a keyword to track."""
    kw = Keyword(
        org_id=auth.org_id,
        site_id=data.site_id,
        keyword=data.keyword,
        target_url=data.target_url,
        intent=data.intent,
        priority=data.priority,
        added_by=auth.user_id,
    )
    db.add(kw)
    await db.commit()
    await db.refresh(kw)
    return {"id": str(kw.id), "keyword": kw.keyword, "message": "Keyword added for tracking"}


@router.delete("/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyword(
    keyword_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a keyword from tracking."""
    result = await db.execute(
        select(Keyword).where(Keyword.id == keyword_id, Keyword.org_id == auth.org_id)
    )
    kw = result.scalar_one_or_none()
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    await db.delete(kw)
    await db.commit()


@router.get("/{keyword_id}/history")
async def get_keyword_history(
    keyword_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get ranking history for a specific keyword."""
    kw = (await db.execute(
        select(Keyword).where(Keyword.id == keyword_id, Keyword.org_id == auth.org_id)
    )).scalar_one_or_none()
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")

    result = await db.execute(
        select(KeywordRanking)
        .where(KeywordRanking.keyword_id == keyword_id)
        .order_by(KeywordRanking.checked_at.desc())
        .limit(90)
    )
    rankings = result.scalars().all()
    return {
        "keyword": kw.keyword,
        "history": [
            {
                "position": r.position,
                "previous_position": r.previous_position,
                "search_volume": r.search_volume,
                "url": r.url,
                "checked_at": r.checked_at.isoformat() if r.checked_at else None,
            }
            for r in rankings
        ],
    }
