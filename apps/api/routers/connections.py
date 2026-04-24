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
from packages.shared.readiness import connection_status_payload
from packages.shared.seo_domain import CONNECTION_CAPABILITY_SUMMARY, connection_capabilities
from config import get_settings

router = APIRouter(tags=["connections"])
settings = get_settings()


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
            "project_root": creds.project_root or "",
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
            "project_root": creds.project_root or "",
            "build_command": creds.build_command,
            "package_manager": creds.package_manager,
        }
    return {}


async def _get_site(db: AsyncSession, site_id: UUID, org_id) -> Site:
    res = await db.execute(select(Site).where(Site.id == site_id, Site.org_id == org_id))
    site = res.scalar_one_or_none()
    if not site:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


def _status_response(site: Site) -> ConnectionStatusResponse:
    snippet_token = str(site.snippet_token) if site.snippet_token else None
    payload = connection_status_payload(site)
    return ConnectionStatusResponse(
        connection_type=site.connection_type,  # type: ignore[arg-type]
        configured=payload["configured"],
        monitoring_mode=payload["monitoring_mode"],
        monitoring_mode_label=payload["monitoring_mode_label"],
        write_integration=payload["write_integration"],
        write_integration_label=payload["write_integration_label"],
        write_integration_configured=payload["write_integration_configured"],
        auto_deploy_capable=payload["auto_deploy_capable"],
        supported_fix_fields=list(payload["supported_fix_fields"]),
        readiness=payload["readiness"],
        readiness_label=payload["readiness_label"],
        explanation=payload["explanation"],
        snippet_token=snippet_token,
        snippet_url=f"{settings.API_URL.rstrip('/')}/api/v1/snippet/{snippet_token}.js" if snippet_token else None,
    )


@router.get("/{site_id}/connection", response_model=ConnectionStatusResponse)
async def get_connection_status(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await _get_site(db, site_id, auth.org_id)
    return _status_response(site)


@router.get("/{site_id}/connection/capabilities")
async def get_connection_capabilities(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await _get_site(db, site_id, auth.org_id)
    return {
        "current_connection_type": site.connection_type,
        "current_status": connection_status_payload(site),
        "capabilities": [
            connection_capabilities(connection_type)
            for connection_type in CONNECTION_CAPABILITY_SUMMARY.keys()
        ],
    }


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
    if creds.sandbox:
        caps = connection_capabilities(creds.connection_type)
        return ConnectionTestResponse(
            success=True,
            message=(
                f"Sandbox check passed for {caps['label']}. "
                "No external credentials were used and nothing was saved."
            ),
        )
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
    if creds.sandbox:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Sandbox checks are test-only and cannot be saved as a real connection",
        )

    if creds.connection_type not in ("crawler", "snippet") and not site.ownership_verified:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Verify site ownership before saving a writable integration. Crawling still works without verification.",
        )

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
    response = _status_response(site)
    response.last_tested_at = datetime.now(timezone.utc).isoformat()
    return response


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
