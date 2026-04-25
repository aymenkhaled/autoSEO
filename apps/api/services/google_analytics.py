"""Google Analytics 4 read-only revenue and conversion helpers."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse
from uuid import UUID

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from models.tables import AnalyticsPageMetric, GoogleAnalyticsConnection, GoogleAnalyticsSyncRun, Site
from packages.shared.encryption import decrypt_credential, encrypt_credential

GA_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
DATA_API = "https://analyticsdata.googleapis.com/v1beta"


def ga_platform_configured(settings: Settings) -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def callback_uri(settings: Settings) -> str:
    return settings.GOOGLE_ANALYTICS_REDIRECT_URI or f"{settings.API_URL.rstrip('/')}/api/v1/google/analytics/callback"


def _signing_secret(settings: Settings) -> bytes:
    return (settings.SUPABASE_JWT_SECRET or "local-dev-secret").encode("utf-8")


def make_state(settings: Settings, *, site_id: UUID, org_id: UUID, user_id: UUID, property_id: str | None = None) -> str:
    payload = {
        "site_id": str(site_id),
        "org_id": str(org_id),
        "user_id": str(user_id),
        "ts": int(time.time()),
    }
    if property_id:
        payload["property_id"] = normalize_property_id(property_id)
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


def build_connect_url(settings: Settings, *, site_id: UUID, org_id: UUID, user_id: UUID, property_id: str | None = None) -> str:
    state = make_state(settings, site_id=site_id, org_id=org_id, user_id=user_id, property_id=property_id)
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": callback_uri(settings),
        "response_type": "code",
        "scope": GA_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def _encrypt_token(org_id: UUID, token_payload: dict) -> tuple[str, str]:
    return encrypt_credential(str(org_id), json.dumps(token_payload, separators=(",", ":"), sort_keys=True))


def _decrypt_token(org_id: UUID, connection: GoogleAnalyticsConnection) -> dict:
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


async def _refresh_access_token(settings: Settings, connection: GoogleAnalyticsConnection) -> str:
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


async def access_token_for_connection(settings: Settings, connection: GoogleAnalyticsConnection) -> str:
    now = datetime.now(timezone.utc)
    expires_at = connection.expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at > now + timedelta(minutes=2):
        return _decrypt_token(connection.org_id, connection).get("access_token", "")
    return await _refresh_access_token(settings, connection)


def normalize_property_id(value: str) -> str:
    cleaned = (value or "").strip()
    if cleaned.startswith("properties/"):
        cleaned = cleaned.split("/", 1)[1]
    if not cleaned.isdigit():
        raise ValueError("GA4 property_id must be the numeric Google Analytics property ID")
    return cleaned


async def upsert_connection(
    db: AsyncSession,
    settings: Settings,
    *,
    site: Site,
    org_id: UUID,
    user_id: UUID,
    code: str,
    property_id: str,
    property_name: str | None = None,
) -> GoogleAnalyticsConnection:
    token_payload = await exchange_code(settings, code=code)
    if not token_payload.get("access_token"):
        raise ValueError("Google did not return an access token")

    property_id = normalize_property_id(property_id)
    expires_in = int(token_payload.get("expires_in") or 3600)
    encrypted, iv = _encrypt_token(org_id, token_payload)
    existing = (
        await db.execute(
            select(GoogleAnalyticsConnection).where(
                GoogleAnalyticsConnection.site_id == site.id,
                GoogleAnalyticsConnection.org_id == org_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        existing.property_id = property_id
        existing.property_name = property_name
        existing.token_encrypted = encrypted
        existing.token_iv = iv
        existing.scopes = [GA_SCOPE]
        existing.expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(60, expires_in - 60))
        existing.connected_by = user_id
        existing.updated_at = datetime.now(timezone.utc)
        connection = existing
    else:
        connection = GoogleAnalyticsConnection(
            org_id=org_id,
            site_id=site.id,
            property_id=property_id,
            property_name=property_name,
            token_encrypted=encrypted,
            token_iv=iv,
            scopes=[GA_SCOPE],
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=max(60, expires_in - 60)),
            connected_by=user_id,
        )
        db.add(connection)
    await db.commit()
    await db.refresh(connection)
    return connection


async def run_report(
    access_token: str,
    *,
    property_id: str,
    start_date: str,
    end_date: str,
    limit: int = 10000,
) -> list[dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{DATA_API}/properties/{property_id}:runReport",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "dateRanges": [{"startDate": start_date, "endDate": end_date}],
                "dimensions": [{"name": "landingPagePlusQueryString"}],
                "metrics": [
                    {"name": "sessions"},
                    {"name": "activeUsers"},
                    {"name": "screenPageViews"},
                    {"name": "keyEvents"},
                    {"name": "totalRevenue"},
                    {"name": "transactions"},
                    {"name": "engagementRate"},
                ],
                "limit": str(max(1, min(limit, 100000))),
                "orderBys": [{"metric": {"metricName": "totalRevenue"}, "desc": True}],
            },
        )
    response.raise_for_status()
    return response.json().get("rows", [])


def _number(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _absolute_page_url(site: Site, path: str) -> str:
    if path.startswith(("http://", "https://")):
        return path
    base = str(site.domain or "").rstrip("/")
    if not base.startswith(("http://", "https://")):
        base = f"https://{base}"
    if path in {"", "(not set)", "/"}:
        return base + "/"
    return base + (path if path.startswith("/") else f"/{path}")


async def sync_site_google_analytics(
    db: AsyncSession,
    settings: Settings,
    *,
    site: Site,
    connection: GoogleAnalyticsConnection,
    days: int = 90,
) -> GoogleAnalyticsSyncRun:
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=max(1, min(days, 480)))).date().isoformat()
    end = (now - timedelta(days=1)).date().isoformat()
    run = GoogleAnalyticsSyncRun(
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
        await db.execute(delete(AnalyticsPageMetric).where(AnalyticsPageMetric.site_id == site.id, AnalyticsPageMetric.org_id == site.org_id))
        rows = await run_report(
            token,
            property_id=connection.property_id,
            start_date=start,
            end_date=end,
        )
        for row in rows:
            dimensions = row.get("dimensionValues") or []
            metrics = row.get("metricValues") or []
            page = dimensions[0].get("value") if dimensions else "/"
            values = [metric.get("value") for metric in metrics]
            db.add(AnalyticsPageMetric(
                org_id=site.org_id,
                site_id=site.id,
                sync_run_id=run.id,
                page_url=_absolute_page_url(site, page or "/"),
                date_start=start,
                date_end=end,
                sessions=_number(values[0] if len(values) > 0 else 0),
                active_users=_number(values[1] if len(values) > 1 else 0),
                views=_number(values[2] if len(values) > 2 else 0),
                key_events=_number(values[3] if len(values) > 3 else 0),
                total_revenue=_number(values[4] if len(values) > 4 else 0),
                transactions=_number(values[5] if len(values) > 5 else 0),
                engagement_rate=_number(values[6] if len(values) > 6 else 0),
            ))
        run.rows_synced = len(rows)
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        connection.last_sync_at = run.completed_at
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)[:1000]
        run.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(run)
    return run
