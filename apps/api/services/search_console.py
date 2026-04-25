"""Google Search Console read-only integration helpers."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlencode, urlparse
from uuid import UUID

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from models.tables import (
    Page,
    SearchConsoleConnection,
    SearchConsoleInspection,
    SearchConsolePageMetric,
    SearchConsoleQueryMetric,
    SearchConsoleSitemap,
    SearchConsoleSyncRun,
    Site,
)
from packages.shared.encryption import decrypt_credential, encrypt_credential

GSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
WEBMASTERS_API = "https://www.googleapis.com/webmasters/v3"
INSPECTION_API = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"


def gsc_platform_configured(settings: Settings) -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def callback_uri(settings: Settings) -> str:
    return settings.GOOGLE_REDIRECT_URI or f"{settings.API_URL.rstrip('/')}/api/v1/google/search-console/callback"


def _signing_secret(settings: Settings) -> bytes:
    return (settings.SUPABASE_JWT_SECRET or "local-dev-secret").encode("utf-8")


def make_state(settings: Settings, *, site_id: UUID, org_id: UUID, user_id: UUID) -> str:
    payload = {
        "site_id": str(site_id),
        "org_id": str(org_id),
        "user_id": str(user_id),
        "ts": int(time.time()),
    }
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("ascii")
    sig = hmac.new(_signing_secret(settings), body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def parse_state(settings: Settings, state: str, *, max_age_seconds: int = 3600) -> dict:
    try:
        body, sig = state.rsplit(".", 1)
    except ValueError as exc:
        raise ValueError("Invalid OAuth state") from exc
    expected = hmac.new(_signing_secret(settings), body.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise ValueError("Invalid OAuth state signature")
    payload = json.loads(base64.urlsafe_b64decode(body.encode("ascii")))
    if int(time.time()) - int(payload.get("ts", 0)) > max_age_seconds:
        raise ValueError("OAuth state expired")
    return payload


def build_connect_url(settings: Settings, *, site_id: UUID, org_id: UUID, user_id: UUID) -> str:
    state = make_state(settings, site_id=site_id, org_id=org_id, user_id=user_id)
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": callback_uri(settings),
        "response_type": "code",
        "scope": GSC_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def _encrypt_token(org_id: UUID, token_payload: dict) -> tuple[str, str]:
    return encrypt_credential(str(org_id), json.dumps(token_payload, separators=(",", ":"), sort_keys=True))


def _decrypt_token(org_id: UUID, connection: SearchConsoleConnection) -> dict:
    plaintext = decrypt_credential(str(org_id), connection.token_encrypted, connection.token_iv)
    return json.loads(plaintext)


async def exchange_code(settings: Settings, *, code: str) -> dict:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": callback_uri(settings),
            },
        )
    response.raise_for_status()
    return response.json()


async def _refresh_access_token(settings: Settings, connection: SearchConsoleConnection) -> str:
    token_payload = _decrypt_token(connection.org_id, connection)
    refresh_token = token_payload.get("refresh_token")
    if not refresh_token:
        return token_payload.get("access_token", "")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
    response.raise_for_status()
    refreshed = response.json()
    token_payload.update(refreshed)
    token_payload["refresh_token"] = refresh_token
    expires_in = int(refreshed.get("expires_in") or 3600)
    connection.expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(60, expires_in - 60))
    connection.token_encrypted, connection.token_iv = _encrypt_token(connection.org_id, token_payload)
    return token_payload.get("access_token", "")


async def access_token_for_connection(settings: Settings, connection: SearchConsoleConnection) -> str:
    now = datetime.now(timezone.utc)
    expires_at = connection.expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at > now + timedelta(minutes=2):
        return _decrypt_token(connection.org_id, connection).get("access_token", "")
    return await _refresh_access_token(settings, connection)


async def list_properties(access_token: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"{WEBMASTERS_API}/sites",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    response.raise_for_status()
    return response.json().get("siteEntry", [])


def choose_property(properties: list[dict], site: Site, requested: str | None = None) -> str | None:
    if requested:
        return requested
    domain = str(site.domain or "").rstrip("/")
    host = urlparse(domain).netloc or domain.replace("https://", "").replace("http://", "").strip("/")
    candidates = {
        domain,
        f"{domain}/",
        f"https://{host}/",
        f"http://{host}/",
        f"sc-domain:{host.removeprefix('www.')}",
    }
    for item in properties:
        url = item.get("siteUrl")
        if url in candidates:
            return url
    return properties[0].get("siteUrl") if properties else None


async def upsert_connection(
    db: AsyncSession,
    settings: Settings,
    *,
    site: Site,
    org_id: UUID,
    user_id: UUID,
    code: str,
    property_url: str | None = None,
) -> SearchConsoleConnection:
    token_payload = await exchange_code(settings, code=code)
    access_token = token_payload.get("access_token", "")
    if not access_token:
        raise ValueError("Google did not return an access token")
    properties = await list_properties(access_token)
    selected_property = choose_property(properties, site, property_url)
    if not selected_property:
        raise ValueError("No Search Console property is available for this Google account")

    expires_in = int(token_payload.get("expires_in") or 3600)
    encrypted, iv = _encrypt_token(org_id, token_payload)
    existing = (
        await db.execute(select(SearchConsoleConnection).where(SearchConsoleConnection.site_id == site.id, SearchConsoleConnection.org_id == org_id))
    ).scalar_one_or_none()
    if existing:
        existing.property_url = selected_property
        existing.token_encrypted = encrypted
        existing.token_iv = iv
        existing.scopes = [GSC_SCOPE]
        existing.expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(60, expires_in - 60))
        existing.connected_by = user_id
        existing.updated_at = datetime.now(timezone.utc)
        connection = existing
    else:
        connection = SearchConsoleConnection(
            org_id=org_id,
            site_id=site.id,
            property_url=selected_property,
            token_encrypted=encrypted,
            token_iv=iv,
            scopes=[GSC_SCOPE],
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=max(60, expires_in - 60)),
            connected_by=user_id,
        )
        db.add(connection)
    site.gsc_property_url = selected_property
    site.gsc_token_encrypted = "stored_in_search_console_connections"
    await db.commit()
    await db.refresh(connection)
    return connection


async def search_analytics_query(
    access_token: str,
    *,
    property_url: str,
    start_date: str,
    end_date: str,
    dimensions: list[str],
    row_limit: int = 25000,
) -> list[dict]:
    encoded_property = quote(property_url, safe="")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{WEBMASTERS_API}/sites/{encoded_property}/searchAnalytics/query",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": dimensions,
                "rowLimit": row_limit,
                "type": "web",
            },
        )
    response.raise_for_status()
    return response.json().get("rows", [])


async def list_sitemaps(access_token: str, *, property_url: str) -> list[dict]:
    encoded_property = quote(property_url, safe="")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"{WEBMASTERS_API}/sites/{encoded_property}/sitemaps",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.status_code == 404:
        return []
    response.raise_for_status()
    return response.json().get("sitemap", [])


async def inspect_url(access_token: str, *, property_url: str, url: str) -> dict | None:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            INSPECTION_API,
            headers={"Authorization": f"Bearer {access_token}"},
            json={"inspectionUrl": url, "siteUrl": property_url, "languageCode": "en-US"},
        )
    if response.status_code in {403, 429}:
        return None
    response.raise_for_status()
    return response.json().get("inspectionResult")


def _number(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


async def sync_site_search_console(
    db: AsyncSession,
    settings: Settings,
    *,
    site: Site,
    connection: SearchConsoleConnection,
    days: int = 90,
    inspect_limit: int = 10,
) -> SearchConsoleSyncRun:
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=max(1, min(days, 480)))).date().isoformat()
    end = (now - timedelta(days=2)).date().isoformat()
    run = SearchConsoleSyncRun(
        org_id=site.org_id,
        site_id=site.id,
        connection_id=connection.id,
        days=days,
        status="running",
        started_at=now,
    )
    db.add(run)
    await db.flush()

    try:
        token = await access_token_for_connection(settings, connection)
        await db.execute(delete(SearchConsolePageMetric).where(SearchConsolePageMetric.site_id == site.id, SearchConsolePageMetric.org_id == site.org_id))
        await db.execute(delete(SearchConsoleQueryMetric).where(SearchConsoleQueryMetric.site_id == site.id, SearchConsoleQueryMetric.org_id == site.org_id))
        await db.execute(delete(SearchConsoleSitemap).where(SearchConsoleSitemap.site_id == site.id, SearchConsoleSitemap.org_id == site.org_id))
        await db.execute(delete(SearchConsoleInspection).where(SearchConsoleInspection.site_id == site.id, SearchConsoleInspection.org_id == site.org_id))

        page_rows = await search_analytics_query(
            token,
            property_url=connection.property_url,
            start_date=start,
            end_date=end,
            dimensions=["page", "device", "country"],
        )
        for row in page_rows:
            keys = row.get("keys") or []
            db.add(SearchConsolePageMetric(
                org_id=site.org_id,
                site_id=site.id,
                sync_run_id=run.id,
                page_url=keys[0] if len(keys) > 0 else site.domain,
                device=keys[1] if len(keys) > 1 else None,
                country=keys[2] if len(keys) > 2 else None,
                date_start=start,
                date_end=end,
                clicks=_number(row.get("clicks")),
                impressions=_number(row.get("impressions")),
                ctr=_number(row.get("ctr")),
                position=_number(row.get("position")),
            ))
        run.pages_synced = len(page_rows)

        query_rows = await search_analytics_query(
            token,
            property_url=connection.property_url,
            start_date=start,
            end_date=end,
            dimensions=["query", "page", "device", "country"],
        )
        for row in query_rows:
            keys = row.get("keys") or []
            db.add(SearchConsoleQueryMetric(
                org_id=site.org_id,
                site_id=site.id,
                sync_run_id=run.id,
                query=keys[0] if len(keys) > 0 else "",
                page_url=keys[1] if len(keys) > 1 else None,
                device=keys[2] if len(keys) > 2 else None,
                country=keys[3] if len(keys) > 3 else None,
                date_start=start,
                date_end=end,
                clicks=_number(row.get("clicks")),
                impressions=_number(row.get("impressions")),
                ctr=_number(row.get("ctr")),
                position=_number(row.get("position")),
            ))
        run.queries_synced = len(query_rows)

        sitemaps = await list_sitemaps(token, property_url=connection.property_url)
        for sitemap in sitemaps:
            db.add(SearchConsoleSitemap(
                org_id=site.org_id,
                site_id=site.id,
                sync_run_id=run.id,
                path=sitemap.get("path") or "",
                is_pending=sitemap.get("isPending"),
                is_sitemaps_index=sitemap.get("isSitemapsIndex"),
                last_submitted=sitemap.get("lastSubmitted"),
                last_downloaded=sitemap.get("lastDownloaded"),
                errors=int(sitemap.get("errors") or 0),
                warnings=int(sitemap.get("warnings") or 0),
                raw=sitemap,
            ))
        run.sitemaps_synced = len(sitemaps)

        important_urls = [
            row[0]
            for row in (
                await db.execute(
                    select(Page.url)
                    .where(Page.site_id == site.id, Page.org_id == site.org_id)
                    .order_by(Page.seo_score.asc().nullslast(), Page.created_at.desc())
                    .limit(max(0, min(inspect_limit, 25)))
                )
            ).all()
        ]
        for url in important_urls:
            result = await inspect_url(token, property_url=connection.property_url, url=url)
            if not result:
                continue
            index_status = result.get("indexStatusResult") or {}
            db.add(SearchConsoleInspection(
                org_id=site.org_id,
                site_id=site.id,
                sync_run_id=run.id,
                url=url,
                verdict=index_status.get("verdict"),
                coverage_state=index_status.get("coverageState"),
                indexing_state=index_status.get("indexingState"),
                robots_txt_state=index_status.get("robotsTxtState"),
                page_fetch_state=index_status.get("pageFetchState"),
                last_crawl_time=index_status.get("lastCrawlTime"),
                google_canonical=index_status.get("googleCanonical"),
                user_canonical=index_status.get("userCanonical"),
                raw=result,
            ))
            run.inspections_synced += 1

        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        connection.last_sync_at = run.completed_at
        site.gsc_property_url = connection.property_url
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)[:1000]
        run.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(run)
    return run
