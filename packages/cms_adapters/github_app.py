"""GitHub App helpers for repo-limited PR access."""
from __future__ import annotations

import time
from dataclasses import dataclass

import httpx
from jose import jwt

GH_API = "https://api.github.com"


class GitHubAppConfigurationError(RuntimeError):
    """Raised when GitHub App credentials are missing or malformed."""


@dataclass(frozen=True)
class InstallationToken:
    token: str
    expires_at: str | None = None
    permissions: dict | None = None
    repositories: list[dict] | None = None


def normalize_private_key(private_key: str) -> str:
    """Support PEMs pasted with literal \n sequences in .env files."""
    return (private_key or "").replace("\\n", "\n").strip()


def github_app_configured(app_id: str | int | None, private_key: str | None) -> bool:
    return bool(str(app_id or "").strip() and normalize_private_key(private_key or ""))


def build_app_jwt(app_id: str | int, private_key: str) -> str:
    key = normalize_private_key(private_key)
    if not str(app_id or "").strip() or not key:
        raise GitHubAppConfigurationError("GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY are required")

    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + 540,
        "iss": str(app_id),
    }
    return jwt.encode(payload, key, algorithm="RS256")


async def create_installation_token(
    *,
    app_id: str | int,
    private_key: str,
    installation_id: int | str,
) -> InstallationToken:
    app_jwt = build_app_jwt(app_id, private_key)
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            f"{GH_API}/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
    if response.status_code not in (200, 201):
        raise GitHubAppConfigurationError(
            f"Could not create GitHub installation token: {response.status_code} {response.text[:200]}"
        )
    data = response.json()
    return InstallationToken(
        token=data.get("token", ""),
        expires_at=data.get("expires_at"),
        permissions=data.get("permissions"),
        repositories=data.get("repositories"),
    )


def build_install_url(*, app_slug: str, state: str) -> str:
    slug = (app_slug or "").strip().strip("/")
    if not slug:
        raise GitHubAppConfigurationError("GITHUB_APP_SLUG is required to build the install URL")
    return f"https://github.com/apps/{slug}/installations/new?state={state}"
