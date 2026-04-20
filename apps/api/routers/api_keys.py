"""API Keys router — generate, list, and revoke API access keys."""
import hashlib
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

from dependencies import get_db, get_current_user
from schemas.auth import AuthContext
from models.tables import ApiKey

router = APIRouter(tags=["api-keys"])

VALID_SCOPES = ["read:sites", "write:sites", "read:issues", "write:fixes", "read:analytics"]


class ApiKeyCreate(BaseModel):
    name: str
    scopes: List[str]
    expires_at: Optional[datetime] = None


@router.get("")
async def list_api_keys(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all API keys for the organization."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.org_id == auth.org_id).order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return {
        "api_keys": [
            {
                "id": str(k.id),
                "name": k.name,
                "key_prefix": k.key_prefix,
                "scopes": k.scopes,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "expires_at": k.expires_at.isoformat() if k.expires_at else None,
                "created_at": k.created_at.isoformat() if k.created_at else None,
            }
            for k in keys
        ],
        "total": len(keys),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: ApiKeyCreate,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new API key. The full key is only shown once."""
    invalid_scopes = [s for s in data.scopes if s not in VALID_SCOPES]
    if invalid_scopes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scopes: {', '.join(invalid_scopes)}. Valid: {', '.join(VALID_SCOPES)}",
        )

    raw_key = f"autoseo_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:16] + "..."

    api_key = ApiKey(
        org_id=auth.org_id,
        name=data.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=data.scopes,
        expires_at=data.expires_at,
    )
    db.add(api_key)
    await db.commit()

    return {
        "id": str(api_key.id),
        "name": api_key.name,
        "key": raw_key,
        "key_prefix": key_prefix,
        "scopes": api_key.scopes,
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
        "message": "Save this key — it will not be shown again.",
    }


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an API key."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.org_id == auth.org_id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    await db.delete(key)
    await db.commit()
