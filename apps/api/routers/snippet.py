"""Snippet router — receives beacon data from the JS snippet (Layer 4).

Phase 2 hardening (from gap analysis):
- Gap 16: persists INP (Core Web Vital since 2024)
- Gap 19: derives device type for mobile/desktop segmentation
- Security 3: lightweight in-process IP rate limit
- Security 5: bot User-Agent filtering
"""
from __future__ import annotations

import json
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from dependencies import get_db
from models.tables import Site, SnippetEvent

router = APIRouter(tags=["snippet"])


# ─── Rate limiting (Security 3) ──────────────────────────────────────────────
_RATE_WINDOW_SECONDS = 60
_RATE_MAX_EVENTS = 120
_ip_hits: dict[str, deque] = defaultdict(deque)


def _rate_limit(ip: str) -> bool:
    now = time.time()
    bucket = _ip_hits[ip]
    while bucket and now - bucket[0] > _RATE_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= _RATE_MAX_EVENTS:
        return False
    bucket.append(now)
    return True


# ─── Bot filtering (Security 5) ──────────────────────────────────────────────
BOT_UA_TOKENS = (
    "googlebot", "bingbot", "slurp", "duckduckbot", "baiduspider",
    "yandexbot", "sogou", "facebot", "facebookexternalhit",
    "ia_archiver", "semrushbot", "ahrefsbot", "mj12bot",
    "curl/", "python-requests", "wget/", "go-http-client",
    "headlesschrome", "phantomjs", "screaming frog",
)


def _is_bot(user_agent: str) -> bool:
    ua = (user_agent or "").lower()
    return any(t in ua for t in BOT_UA_TOKENS)


def _detect_device(user_agent: str, viewport: int | None) -> str:
    ua = (user_agent or "").lower()
    if "mobile" in ua or "android" in ua or "iphone" in ua:
        return "mobile"
    if "ipad" in ua or "tablet" in ua:
        return "tablet"
    if viewport and viewport < 768:
        return "mobile"
    if viewport and viewport < 1024:
        return "tablet"
    return "desktop"


@router.post("/collect", status_code=status.HTTP_204_NO_CONTENT)
async def collect_snippet_data(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive SEO + field-performance data from the JS snippet.

    Public endpoint — authentication is via the site's snippet token.
    """
    # Rate limit by client IP
    client_ip = (request.client.host if request.client else "0.0.0.0")
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    if not _rate_limit(client_ip):
        # Silent drop — don't tell abusers the limit
        return

    # Parse body (sendBeacon may use text/plain)
    try:
        body = await request.json()
    except Exception:
        raw = await request.body()
        try:
            body = json.loads(raw)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON body",
            )

    user_agent = request.headers.get("user-agent", "")
    if _is_bot(user_agent):
        # Silently drop bot traffic — would corrupt RUM data
        return

    # Honour Do Not Track when client signals it
    if request.headers.get("dnt") == "1":
        return

    token = body.get("token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing snippet token",
        )
    try:
        token_uuid = UUID(token)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token format",
        )

    result = await db.execute(select(Site).where(Site.snippet_token == token_uuid))
    site = result.scalar_one_or_none()
    if not site:
        # Silently ignore — don't reveal whether token exists
        return

    viewport = body.get("viewport_width")
    try:
        viewport_int = int(viewport) if viewport is not None else None
    except (TypeError, ValueError):
        viewport_int = None

    event = SnippetEvent(
        site_id=site.id,
        org_id=site.org_id,
        page_url=body.get("url", ""),
        title=body.get("title"),
        meta_description=body.get("meta_description"),
        canonical_url=body.get("canonical"),
        h1_text=body.get("h1"),
        schema_json=body.get("schema"),
        lcp_ms=_safe_int(body.get("lcp")),
        cls_score=body.get("cls"),
        ttfb_ms=_safe_int(body.get("ttfb")),
        inp_ms=_safe_int(body.get("inp")),         # Gap 16
        fcp_ms=_safe_int(body.get("fcp")),
        device_type=_detect_device(user_agent, viewport_int),  # Gap 19
        user_agent=user_agent,
        viewport_width=viewport_int,
    )
    db.add(event)
    await db.commit()


def _safe_int(v) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
