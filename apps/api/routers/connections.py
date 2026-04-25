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
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_db, get_current_user
from schemas.auth import AuthContext
from schemas.connection import (
    ConnectionCredentials,
    ConnectionStatusResponse,
    ConnectionTestResponse,
)
from models.tables import ConnectionCertification, Site
from packages.cms_adapters import get_adapter
from packages.shared.encryption import encrypt_credential
from packages.shared.readiness import connection_status_payload
from packages.shared.seo_domain import CONNECTION_CAPABILITY_SUMMARY, connection_capabilities
from config import get_settings
from services.github_connection import decrypt_site_credentials, github_connection_metadata

router = APIRouter(tags=["connections"])
settings = get_settings()


class CertificationRequest(BaseModel):
    mode: Literal["sandbox", "credentials", "safe_fix"] = "sandbox"
    credentials: ConnectionCredentials | None = None
    test_page_id: str | None = None
    field: str = "title"
    test_value: str = "AutoSEO certification test - revert if visible"
    confirm_safe_fix: bool = False


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
            "token": creds.github_token,
            "access_method": "fine_grained_token",
            "branch": creds.branch or "main",
            "project_root": creds.project_root or "",
            "build_command": creds.build_command,
            "package_manager": creds.package_manager,
        }
    return {}


def _saved_adapter_kwargs(connection_type: str, site: Site, org_id) -> dict:
    creds = decrypt_site_credentials(str(org_id), site)
    if connection_type == "wordpress":
        return {
            "site_url": site.cms_endpoint or site.domain,
            "username": creds.get("username") or "",
            "app_password": creds.get("app_password") or "",
        }
    if connection_type == "shopify":
        return {
            "shop_domain": creds.get("shop_domain") or site.cms_endpoint or "",
            "access_token": creds.get("access_token") or "",
        }
    if connection_type == "webflow":
        return {"site_id": creds.get("site_id") or "", "token": creds.get("token") or ""}
    if connection_type == "github":
        return {
            "owner": creds.get("owner") or (site.github_repo or "/").split("/")[0],
            "repo": creds.get("repo") or (site.github_repo or "/").split("/", 1)[-1],
            "token": creds.get("token") or creds.get("github_token") or "",
            "branch": creds.get("branch") or site.github_branch or "main",
            "project_root": creds.get("project_root") or "",
        }
    if connection_type == "crawler":
        return {"domain": site.domain}
    if connection_type == "snippet":
        return {"site_token": str(site.snippet_token) if site.snippet_token else None}
    return {}


async def _get_site(db: AsyncSession, site_id: UUID, org_id) -> Site:
    res = await db.execute(select(Site).where(Site.id == site_id, Site.org_id == org_id))
    site = res.scalar_one_or_none()
    if not site:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


def _status_response(site: Site, org_id=None) -> ConnectionStatusResponse:
    snippet_token = str(site.snippet_token) if site.snippet_token else None
    payload = connection_status_payload(site)
    github_meta = github_connection_metadata(str(org_id), site) if org_id and site.connection_type == "github" else {
        "access_method": "none",
        "permission_level": "audit_only",
        "selected_repository": None,
        "project_root": "",
        "build_command": None,
        "package_manager": None,
    }
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
        access_method=github_meta["access_method"],
        permission_level=github_meta["permission_level"],
        selected_repository=github_meta["selected_repository"],
        project_root=github_meta["project_root"],
        build_command=github_meta["build_command"],
        package_manager=github_meta["package_manager"],
    )


@router.get("/{site_id}/connection", response_model=ConnectionStatusResponse)
async def get_connection_status(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await _get_site(db, site_id, auth.org_id)
    return _status_response(site, auth.org_id)


@router.get("/{site_id}/connection/capabilities")
async def get_connection_capabilities(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await _get_site(db, site_id, auth.org_id)
    certifications = (
        await db.execute(
            select(ConnectionCertification).where(
                ConnectionCertification.site_id == site_id,
                ConnectionCertification.org_id == auth.org_id,
            )
        )
    ).scalars().all()
    cert_map = {
        item.connection_type: {
            "status": item.status,
            "message": item.message,
            "last_tested_at": item.last_tested_at.isoformat() if item.last_tested_at else None,
            "safe_fix_tested_at": item.safe_fix_tested_at.isoformat() if item.safe_fix_tested_at else None,
        }
        for item in certifications
    }
    return {
        "current_connection_type": site.connection_type,
        "current_status": connection_status_payload(site),
        "capabilities": [
            {
                **connection_capabilities(connection_type),
                "certification": cert_map.get(connection_type, {
                    "status": "not_tested",
                    "message": "This connection has not been certified for this site yet.",
                    "last_tested_at": None,
                    "safe_fix_tested_at": None,
                }),
            }
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
        site.github_installation_id = None

    await db.commit()
    await db.refresh(site)
    response = _status_response(site, auth.org_id)
    response.last_tested_at = datetime.now(timezone.utc).isoformat()
    return response


@router.post("/{site_id}/connections/{connection_type}/certify")
async def certify_connection(
    site_id: UUID,
    connection_type: str,
    data: CertificationRequest | None = None,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await _get_site(db, site_id, auth.org_id)
    request = data or CertificationRequest()
    if connection_type not in CONNECTION_CAPABILITY_SUMMARY:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unsupported connection type")

    now = datetime.now(timezone.utc)
    certification = (
        await db.execute(
            select(ConnectionCertification).where(
                ConnectionCertification.site_id == site_id,
                ConnectionCertification.org_id == auth.org_id,
                ConnectionCertification.connection_type == connection_type,
            )
        )
    ).scalar_one_or_none()
    if not certification:
        certification = ConnectionCertification(
            org_id=auth.org_id,
            site_id=site_id,
            connection_type=connection_type,
        )
        db.add(certification)

    if request.mode == "sandbox":
        certification.status = "sandbox_only"
        certification.message = "Sandbox certification passed. This proves UI/API wiring only; it does not prove real platform credentials."
        certification.details = {"mode": "sandbox", "external_calls": False}
        certification.last_tested_at = now
    else:
        if connection_type in {"crawler", "snippet"}:
            certification.status = "production_ready" if connection_type == "crawler" else "credentials_tested"
            certification.message = "Monitoring connection certified. This method remains read-only for deployment."
            certification.details = {"mode": request.mode, "read_only": True}
            certification.last_tested_at = now
        else:
            if not site.ownership_verified:
                raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Verify site ownership before certifying writable integrations.")
            try:
                if request.credentials:
                    adapter = get_adapter(connection_type, **_build_kwargs(request.credentials, site))
                else:
                    adapter = get_adapter(connection_type, **_saved_adapter_kwargs(connection_type, site, auth.org_id))
                ok = await adapter.test_connection()
            except Exception as exc:
                ok = False
                certification.details = {"mode": request.mode, "error": str(exc)}
            certification.last_tested_at = now
            if not ok:
                certification.status = "failed"
                certification.message = "Credential test failed. AutoSEO will not mark this integration production-ready."
            elif request.mode == "safe_fix":
                if not request.confirm_safe_fix or not request.test_page_id:
                    certification.status = "credentials_tested"
                    certification.message = "Credentials work. Safe-fix certification needs a staging/draft test page ID and explicit confirmation."
                    certification.details = {"mode": "safe_fix", "safe_fix_tested": False}
                else:
                    result = await adapter.apply_fix(request.test_page_id, request.field, request.test_value)
                    certification.status = "safe_fix_tested" if result.success else "failed"
                    certification.safe_fix_tested_at = now if result.success else certification.safe_fix_tested_at
                    certification.message = result.message
                    certification.details = {
                        "mode": "safe_fix",
                        "test_page_id": request.test_page_id,
                        "field": request.field,
                        "success": result.success,
                        "rollback_value_present": bool(result.rollback_value),
                    }
            else:
                certification.status = "credentials_tested"
                certification.message = "Credentials work. Run a safe staging/draft fix test before marking this production-ready."
                certification.details = {"mode": "credentials", "safe_fix_tested": False}

    certification.updated_at = now
    await db.commit()
    await db.refresh(certification)
    return {
        "site_id": str(site_id),
        "connection_type": connection_type,
        "status": certification.status,
        "message": certification.message,
        "details": certification.details or {},
        "last_tested_at": certification.last_tested_at.isoformat() if certification.last_tested_at else None,
        "safe_fix_tested_at": certification.safe_fix_tested_at.isoformat() if certification.safe_fix_tested_at else None,
    }


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
    site.github_installation_id = None
    site.github_repo = None
    site.github_branch = "main"
    await db.commit()
