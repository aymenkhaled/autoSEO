"""Per-site CMS connection management.

Endpoints
---------
GET    /sites/{site_id}/connection           → current connection status
POST   /sites/{site_id}/connection/test      → live credential test (no save)
PUT    /sites/{site_id}/connection           → encrypt + save credentials
DELETE /sites/{site_id}/connection           → wipe credentials
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_db, get_current_user
from schemas.auth import AuthContext
from schemas.connection import (
    ConnectionCredentials,
    ConnectionStatusResponse,
    ConnectionTestResponse,
)
from models.tables import Site
from packages.cms_adapters import get_adapter
from packages.shared.encryption import encrypt_credential

router = APIRouter(tags=["connections"])


def _build_kwargs(creds: ConnectionCredentials, site: Site | None = None) -> dict:
    ct = creds.connection_type
    if ct == "wordpress":
        return {
            "site_url": creds.site_url or (site.cms_endpoint if site else "") or (site.domain if site else ""),
            "username": creds.username or "",
            "app_password": creds.app_password or "",
        }
    if ct == "shopify":
        return {
            "shop_domain": creds.shop_domain or (site.cms_endpoint if site else ""),
            "access_token": creds.access_token or "",
        }
    if ct == "webflow":
        return {"site_id": creds.site_id or "", "token": creds.token or ""}
    if ct == "github":
        return {
            "owner": creds.owner or "",
            "repo": creds.repo or "",
            "token": creds.github_token or "",
            "branch": creds.branch or "main",
        }
    if ct == "crawler":
        return {"domain": site.domain if site else ""}
    if ct == "snippet":
        return {"site_token": str(site.snippet_token) if site and site.snippet_token else None}
    return {}


def _persistable_creds(creds: ConnectionCredentials) -> dict:
    """Return only the fields that should be encrypted to disk for this type.

    We intentionally store creds as a JSON blob so adding a new connection type
    doesn't require a migration.
    """
    ct = creds.connection_type
    if ct == "wordpress":
        return {"username": creds.username, "app_password": creds.app_password}
    if ct == "shopify":
        return {"shop_domain": creds.shop_domain, "access_token": creds.access_token}
    if ct == "webflow":
        return {"site_id": creds.site_id, "token": creds.token}
    if ct == "github":
        return {
            "owner": creds.owner, "repo": creds.repo,
            "token": creds.github_token, "branch": creds.branch or "main",
        }
    return {}


async def _get_site(db: AsyncSession, site_id: UUID, org_id) -> Site:
    res = await db.execute(select(Site).where(Site.id == site_id, Site.org_id == org_id))
    site = res.scalar_one_or_none()
    if not site:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


@router.get("/{site_id}/connection", response_model=ConnectionStatusResponse)
async def get_connection_status(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await _get_site(db, site_id, auth.org_id)
    snippet_token = str(site.snippet_token) if site.snippet_token else None
    return ConnectionStatusResponse(
        connection_type=site.connection_type,  # type: ignore[arg-type]
        configured=bool(site.cms_token_encrypted) or site.connection_type in ("crawler", "snippet"),
        snippet_token=snippet_token,
        snippet_url=f"/snippet/{snippet_token}.js" if snippet_token else None,
    )


@router.post("/{site_id}/connection/test", response_model=ConnectionTestResponse)
async def test_connection(
    site_id: UUID,
    creds: ConnectionCredentials,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run the adapter's read-only test_connection() with the supplied creds.

    Does NOT persist anything — use PUT /connection to save after a successful test.
    """
    site = await _get_site(db, site_id, auth.org_id)
    try:
        adapter = get_adapter(creds.connection_type, **_build_kwargs(creds, site))
    except Exception as exc:
        return ConnectionTestResponse(success=False, message=f"Adapter setup failed: {exc}")
    try:
        ok = await adapter.test_connection()
    except Exception as exc:
        return ConnectionTestResponse(success=False, message=f"Connection failed: {exc}")
    return ConnectionTestResponse(
        success=ok,
        message="Connected successfully" if ok else "Authentication or endpoint check failed",
    )


@router.put("/{site_id}/connection", response_model=ConnectionStatusResponse)
async def save_connection(
    site_id: UUID,
    creds: ConnectionCredentials,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Persist credentials (encrypted with per-tenant AES-256-GCM key)."""
    site = await _get_site(db, site_id, auth.org_id)

    # Always re-test before saving to avoid storing dud creds
    if creds.connection_type not in ("crawler", "snippet"):
        try:
            adapter = get_adapter(creds.connection_type, **_build_kwargs(creds, site))
            if not await adapter.test_connection():
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail="Credential test failed — not saving",
                )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Connection error: {exc}")

    site.connection_type = creds.connection_type
    persist = _persistable_creds(creds)
    if persist:
        ciphertext, iv = encrypt_credential(str(auth.org_id), json.dumps(persist))
        site.cms_token_encrypted = ciphertext
        site.cms_token_iv = iv
    if creds.connection_type == "wordpress" and creds.site_url:
        site.cms_endpoint = creds.site_url
    if creds.connection_type == "shopify" and creds.shop_domain:
        site.cms_endpoint = creds.shop_domain
    if creds.connection_type == "github":
        site.github_repo = f"{creds.owner}/{creds.repo}" if creds.owner and creds.repo else site.github_repo
        site.github_branch = creds.branch or "main"

    await db.commit()
    await db.refresh(site)

    snippet_token = str(site.snippet_token) if site.snippet_token else None
    return ConnectionStatusResponse(
        connection_type=site.connection_type,  # type: ignore[arg-type]
        configured=True,
        last_tested_at=datetime.now(timezone.utc).isoformat(),
        snippet_token=snippet_token,
        snippet_url=f"/snippet/{snippet_token}.js" if snippet_token else None,
    )


@router.delete("/{site_id}/connection", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await _get_site(db, site_id, auth.org_id)
    site.cms_token_encrypted = None
    site.cms_token_iv = None
    site.connection_type = "crawler"
    await db.commit()
