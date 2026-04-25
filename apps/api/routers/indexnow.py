"""IndexNow setup and submission routes."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dependencies import get_current_user, get_db
from models.tables import IndexNowKey, IndexNowSubmission, Site
from schemas.auth import AuthContext
from services.indexnow import get_or_create_key, submit_urls, verify_key

router = APIRouter(tags=["indexnow"])
settings = get_settings()


class IndexNowSubmitRequest(BaseModel):
    urls: list[str] = Field(default_factory=list)


async def _site(db: AsyncSession, site_id: UUID, org_id: UUID) -> Site:
    site = (
        await db.execute(select(Site).where(Site.id == site_id, Site.org_id == org_id))
    ).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


def _key_payload(record: IndexNowKey | None) -> dict:
    return {
        "configured": bool(record),
        "key": record.key if record else None,
        "key_location": record.key_location if record else None,
        "verified": bool(record and record.verified),
        "last_verified_at": record.last_verified_at.isoformat() if record and record.last_verified_at else None,
        "instructions": (
            f"Create a public UTF-8 text file at {record.key_location} with exactly this content: {record.key}"
            if record else "Create an IndexNow key before submitting changed URLs."
        ),
    }


@router.get("/sites/{site_id}/indexnow/status")
async def indexnow_status(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await _site(db, site_id, auth.org_id)
    record = (
        await db.execute(select(IndexNowKey).where(IndexNowKey.site_id == site.id, IndexNowKey.org_id == auth.org_id))
    ).scalar_one_or_none()
    latest = (
        await db.execute(
            select(IndexNowSubmission)
            .where(IndexNowSubmission.site_id == site.id, IndexNowSubmission.org_id == auth.org_id)
            .order_by(IndexNowSubmission.created_at.desc())
            .limit(5)
        )
    ).scalars().all()
    return {
        "site_id": str(site.id),
        "readiness": "working" if record and record.verified else "setup_required",
        "readiness_label": "IndexNow verified" if record and record.verified else "IndexNow setup required",
        **_key_payload(record),
        "recent_submissions": [
            {
                "id": str(row.id),
                "urls": row.urls,
                "status_code": row.status_code,
                "success": row.success,
                "response_body": row.response_body,
                "submitted_at": row.submitted_at.isoformat() if row.submitted_at else None,
            }
            for row in latest
        ],
    }


@router.post("/sites/{site_id}/indexnow/setup")
async def indexnow_setup(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await _site(db, site_id, auth.org_id)
    record = await get_or_create_key(db, site=site, user_id=auth.user_id)
    await verify_key(db, record=record)
    return {
        "site_id": str(site.id),
        "message": "IndexNow key prepared. Upload the key file, then run setup again or submit after verification passes.",
        **_key_payload(record),
    }


@router.post("/sites/{site_id}/indexnow/submit")
async def indexnow_submit(
    site_id: UUID,
    data: IndexNowSubmitRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await _site(db, site_id, auth.org_id)
    record = (
        await db.execute(select(IndexNowKey).where(IndexNowKey.site_id == site.id, IndexNowKey.org_id == auth.org_id))
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="IndexNow is not set up for this site.")
    if not await verify_key(db, record=record):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"IndexNow key file is not verified. Publish {record.key_location} with the key content before submitting URLs.",
        )
    submission = await submit_urls(db, settings, site=site, record=record, urls=data.urls)
    return {
        "id": str(submission.id),
        "success": submission.success,
        "status_code": submission.status_code,
        "submitted_urls": submission.urls,
        "response_body": submission.response_body,
    }
