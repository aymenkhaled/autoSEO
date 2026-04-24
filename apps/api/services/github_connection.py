"""Resolve a site's GitHub connection into an adapter."""
from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException, status

from config import get_settings
from models.tables import Site
from packages.cms_adapters.github_adapter import GitHubAdapter
from packages.cms_adapters.github_app import GitHubAppConfigurationError, create_installation_token
from packages.shared.encryption import decrypt_credential


def decrypt_site_credentials(org_id: str, site: Site) -> dict[str, Any]:
    if not site.cms_token_encrypted or not site.cms_token_iv:
        return {}
    plaintext = decrypt_credential(org_id, site.cms_token_encrypted, site.cms_token_iv)
    try:
        return json.loads(plaintext)
    except json.JSONDecodeError:
        return {"token": plaintext, "access_method": "fine_grained_token"}


def github_connection_metadata(org_id: str, site: Site) -> dict[str, Any]:
    creds = decrypt_site_credentials(org_id, site)
    access_method = creds.get("access_method")
    if site.connection_type != "github":
        access_method = "none"
    elif access_method not in {"github_app", "fine_grained_token"}:
        access_method = "github_app" if site.github_installation_id else "fine_grained_token" if creds.get("token") else "none"

    selected_repository = site.github_repo or (
        f"{creds.get('owner')}/{creds.get('repo')}" if creds.get("owner") and creds.get("repo") else None
    )
    permission_level = (
        "pr_only"
        if access_method == "github_app"
        else "advanced_token"
        if access_method == "fine_grained_token"
        else "audit_only"
    )
    return {
        "access_method": access_method,
        "permission_level": permission_level,
        "selected_repository": selected_repository,
        "project_root": creds.get("project_root") or "",
        "build_command": creds.get("build_command"),
        "package_manager": creds.get("package_manager"),
    }


async def github_adapter_for_site(org_id: str, site: Site) -> tuple[GitHubAdapter, dict[str, Any]]:
    if site.connection_type != "github":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="GitHub is not configured for this site")

    settings = get_settings()
    creds = decrypt_site_credentials(org_id, site)
    owner = creds.get("owner") or (site.github_repo or "/").split("/")[0]
    repo = creds.get("repo") or (site.github_repo or "/").split("/", 1)[-1]
    branch = creds.get("branch") or site.github_branch or "main"
    project_root = creds.get("project_root") or ""
    token = creds.get("token") or creds.get("github_token") or ""
    access_method = creds.get("access_method") or ("github_app" if site.github_installation_id else "fine_grained_token")

    if access_method == "github_app":
        installation_id = creds.get("installation_id") or site.github_installation_id
        if not installation_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="GitHub App installation is missing")
        try:
            installation = await create_installation_token(
                app_id=settings.GITHUB_APP_ID,
                private_key=settings.GITHUB_APP_PRIVATE_KEY,
                installation_id=installation_id,
            )
        except GitHubAppConfigurationError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        token = installation.token

    if not owner or not repo or not token:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="GitHub owner, repository, and access token/installation are required",
        )

    adapter = GitHubAdapter(
        owner=owner,
        repo=repo,
        token=token,
        branch=branch,
        project_root=project_root,
    )
    return adapter, {
        **creds,
        "owner": owner,
        "repo": repo,
        "branch": branch,
        "project_root": project_root,
        "access_method": access_method,
    }
