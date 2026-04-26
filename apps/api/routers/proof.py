"""Before/after proof APIs."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_current_user, get_db
from models.tables import Site
from schemas.auth import AuthContext
from services.proof_loop import proof_summary

router = APIRouter(tags=["proof"])


@router.get("/sites/{site_id}/proof")
async def site_proof(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = (await db.execute(select(Site).where(Site.id == site_id, Site.org_id == auth.org_id))).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return await proof_summary(db, site=site)
