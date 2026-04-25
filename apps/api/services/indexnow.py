"""IndexNow setup and URL submission helpers."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from models.tables import IndexNowKey, IndexNowSubmission, Site
from packages.crawler.url_utils import is_safe_url


def _host(site: Site) -> str:
    domain = str(site.domain or "")
    if not domain.startswith(("http://", "https://")):
        domain = f"https://{domain}"
    parsed = urlparse(domain)
    return parsed.netloc or parsed.path.strip("/")


def _base_url(site: Site) -> str:
    domain = str(site.domain or "")
    if not domain.startswith(("http://", "https://")):
        domain = f"https://{domain}"
    return domain.rstrip("/")


def _same_host(site: Site, url: str) -> bool:
    expected = _host(site).lower()
    parsed = urlparse(url)
    return bool(parsed.scheme in {"http", "https"} and parsed.netloc.lower() == expected)


async def get_or_create_key(db: AsyncSession, *, site: Site, user_id) -> IndexNowKey:
    existing = (
        await db.execute(
            select(IndexNowKey).where(IndexNowKey.site_id == site.id, IndexNowKey.org_id == site.org_id)
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    key = secrets.token_hex(16)
    record = IndexNowKey(
        org_id=site.org_id,
        site_id=site.id,
        key=key,
        key_location=f"{_base_url(site)}/{key}.txt",
        created_by=user_id,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def verify_key(db: AsyncSession, *, record: IndexNowKey) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.get(record.key_location)
        ok = response.status_code == 200 and response.text.strip() == record.key
    except Exception:
        ok = False
    record.verified = ok
    record.last_verified_at = datetime.now(timezone.utc) if ok else record.last_verified_at
    await db.commit()
    await db.refresh(record)
    return ok


async def submit_urls(
    db: AsyncSession,
    settings: Settings,
    *,
    site: Site,
    record: IndexNowKey,
    urls: list[str],
) -> IndexNowSubmission:
    clean_urls = []
    for url in urls[:10000]:
        if is_safe_url(url) and _same_host(site, url):
            clean_urls.append(url)
    if not clean_urls:
        submission = IndexNowSubmission(
            org_id=site.org_id,
            site_id=site.id,
            key_id=record.id,
            urls=[],
            success=False,
            response_body="No safe same-host URLs were provided.",
        )
        db.add(submission)
        await db.commit()
        await db.refresh(submission)
        return submission

    payload = {
        "host": _host(site),
        "key": record.key,
        "keyLocation": record.key_location,
        "urlList": clean_urls,
    }
    submission = IndexNowSubmission(
        org_id=site.org_id,
        site_id=site.id,
        key_id=record.id,
        urls=clean_urls,
        submitted_at=datetime.now(timezone.utc),
    )
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                settings.INDEXNOW_ENDPOINT,
                json=payload,
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
        submission.status_code = response.status_code
        submission.success = response.status_code in {200, 202}
        submission.response_body = response.text[:1000]
    except Exception as exc:
        submission.success = False
        submission.response_body = str(exc)[:1000]
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    return submission
