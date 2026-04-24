"""GitHub App and repository analysis endpoints."""
from __future__ import annotations

import hmac
import hashlib
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dependencies import get_current_user, get_db
from models.tables import Site
from packages.cms_adapters.github_app import (
    GitHubAppConfigurationError,
    build_install_url,
    github_app_configured,
)
from packages.shared.encryption import encrypt_credential
from schemas.auth import AuthContext
from services.github_connection import github_adapter_for_site

router = APIRouter(tags=["github"])


class CompleteInstallRequest(BaseModel):
    site_id: UUID
    installation_id: int
    owner: str
    repo: str
    branch: str = "main"
    project_root: str = ""
    build_command: str | None = None
    package_manager: str | None = None


async def _get_site(db: AsyncSession, site_id: UUID, org_id) -> Site:
    site = (
        await db.execute(select(Site).where(Site.id == site_id, Site.org_id == org_id))
    ).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


def _state_for_site(site_id: UUID, org_id, secret: str) -> str:
    body = f"{org_id}:{site_id}"
    sig = hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{site_id}:{sig}"


@router.get("/github/app/install-url")
async def github_app_install_url(
    site_id: UUID = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the repo-limited GitHub App install URL for a site."""
    settings = get_settings()
    site = await _get_site(db, site_id, auth.org_id)
    state = _state_for_site(site.id, auth.org_id, settings.SUPABASE_JWT_SECRET)

    configured = bool(
        settings.GITHUB_APP_SLUG
        and github_app_configured(settings.GITHUB_APP_ID, settings.GITHUB_APP_PRIVATE_KEY)
    )
    if not configured:
        return {
            "configured": False,
            "install_url": None,
            "state": state,
            "requires_verification": not site.ownership_verified,
            "message": "Configure GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY, and GITHUB_APP_SLUG before using GitHub App install.",
        }

    try:
        install_url = build_install_url(app_slug=settings.GITHUB_APP_SLUG, state=state)
    except GitHubAppConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return {
        "configured": True,
        "install_url": install_url,
        "state": state,
        "requires_verification": not site.ownership_verified,
        "message": "Install the AutoSEO GitHub App on one selected repository, then complete the connection in AutoSEO.",
    }


@router.post("/github/app/complete-install")
async def complete_github_app_install(
    data: CompleteInstallRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Persist a GitHub App installation as the site's PR-only write integration."""
    site = await _get_site(db, data.site_id, auth.org_id)
    if not site.ownership_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify site ownership before saving a GitHub write integration.",
        )

    settings = get_settings()
    if not github_app_configured(settings.GITHUB_APP_ID, settings.GITHUB_APP_PRIVATE_KEY):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub App credentials are not configured.",
        )

    persist = {
        "access_method": "github_app",
        "installation_id": data.installation_id,
        "owner": data.owner,
        "repo": data.repo,
        "branch": data.branch or "main",
        "project_root": data.project_root or "",
        "build_command": data.build_command,
        "package_manager": data.package_manager,
    }
    ciphertext, iv = encrypt_credential(str(auth.org_id), json.dumps(persist))
    site.connection_type = "github"
    site.cms_token_encrypted = ciphertext
    site.cms_token_iv = iv
    site.github_installation_id = data.installation_id
    site.github_repo = f"{data.owner}/{data.repo}"
    site.github_branch = data.branch or "main"

    # Validate the installation token can access the selected repository before saving.
    adapter, _creds = await github_adapter_for_site(str(auth.org_id), site)
    if not await adapter.test_connection():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GitHub App cannot access this repository")

    await db.commit()
    return {
        "success": True,
        "access_method": "github_app",
        "permission_level": "pr_only",
        "selected_repository": site.github_repo,
        "project_root": data.project_root or "",
        "build_command": data.build_command,
        "package_manager": data.package_manager,
    }


@router.get("/sites/{site_id}/github/repo-analysis")
async def analyze_github_repo(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await _get_site(db, site_id, auth.org_id)
    adapter, creds = await github_adapter_for_site(str(auth.org_id), site)
    analysis = await adapter.analyze_static_app(creds.get("project_root") or "")
    candidates = await adapter.candidate_files_for_issue("duplicate_title", project_root=creds.get("project_root") or "")
    return {
        "site_id": str(site.id),
        "selected_repository": site.github_repo,
        "access_method": creds.get("access_method"),
        "permission_level": "pr_only" if creds.get("access_method") == "github_app" else "advanced_token",
        "analysis": analysis,
        "candidate_files": candidates[:12],
    }
