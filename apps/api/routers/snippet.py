"""Snippet router — serves the JS snippet and collects monitoring events."""
from __future__ import annotations

import json
import time
from collections import defaultdict, deque
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dependencies import get_current_user, get_db
from models.tables import Site, SnippetEvent
from schemas.auth import AuthContext

router = APIRouter(tags=["snippet"])
settings = get_settings()

_RATE_WINDOW_SECONDS = 60
_RATE_MAX_EVENTS = 120
_ip_hits: dict[str, deque] = defaultdict(deque)
_SNIPPET_SOURCE = Path(__file__).resolve().parents[3] / "packages" / "snippet" / "snippet.js"

BOT_UA_TOKENS = (
    "googlebot",
    "bingbot",
    "slurp",
    "duckduckbot",
    "baiduspider",
    "yandexbot",
    "sogou",
    "facebot",
    "facebookexternalhit",
    "ia_archiver",
    "semrushbot",
    "ahrefsbot",
    "mj12bot",
    "curl/",
    "python-requests",
    "wget/",
    "go-http-client",
    "headlesschrome",
    "phantomjs",
    "screaming frog",
)


def _rate_limit(ip: str) -> bool:
    now = time.time()
    bucket = _ip_hits[ip]
    while bucket and now - bucket[0] > _RATE_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= _RATE_MAX_EVENTS:
        return False
    bucket.append(now)
    return True


def _is_bot(user_agent: str) -> bool:
    lowered = (user_agent or "").lower()
    return any(token in lowered for token in BOT_UA_TOKENS)


def _detect_device(user_agent: str, viewport: int | None) -> str:
    lowered = (user_agent or "").lower()
    if "mobile" in lowered or "android" in lowered or "iphone" in lowered:
        return "mobile"
    if "ipad" in lowered or "tablet" in lowered:
        return "tablet"
    if viewport and viewport < 768:
        return "mobile"
    if viewport and viewport < 1024:
        return "tablet"
    return "desktop"


def _safe_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _snippet_collect_url() -> str:
    return f"{settings.API_URL.rstrip('/')}/api/v1/snippet/collect"


@router.get("/install-code")
async def get_install_code(
    site_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = (
        await db.execute(select(Site).where(Site.id == site_id, Site.org_id == auth.org_id))
    ).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    snippet_url = f"{settings.API_URL.rstrip('/')}/api/v1/snippet/{site.snippet_token}.js"
    return {
        "site_id": str(site.id),
        "snippet_token": str(site.snippet_token),
        "snippet_url": snippet_url,
        "collect_url": _snippet_collect_url(),
        "script_tag": f'<script src="{snippet_url}" async></script>',
    }


@router.get("/{site_token}.js", include_in_schema=False)
async def serve_snippet(site_token: str, db: AsyncSession = Depends(get_db)):
    try:
        token_uuid = UUID(site_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snippet not found") from exc

    site = (await db.execute(select(Site).where(Site.snippet_token == token_uuid))).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snippet not found")

    if not _SNIPPET_SOURCE.exists():
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Snippet source missing")

    bootstrap = (
        "(function(){"
        "var s=document.currentScript;"
        f"if(s&&!s.getAttribute('data-token'))s.setAttribute('data-token','{site.snippet_token}');"
        f"if(s&&!s.getAttribute('data-endpoint'))s.setAttribute('data-endpoint','{_snippet_collect_url()}');"
        "})();\n"
    )
    source = _SNIPPET_SOURCE.read_text(encoding="utf-8")
    return Response(
        content=bootstrap + source,
        media_type="application/javascript",
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.post("/collect", status_code=status.HTTP_204_NO_CONTENT)
async def collect_snippet_data(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else "0.0.0.0"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    if not _rate_limit(client_ip):
        return

    try:
        body = await request.json()
    except Exception:
        raw = await request.body()
        try:
            body = json.loads(raw)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body") from exc

    user_agent = request.headers.get("user-agent", "")
    if _is_bot(user_agent) or request.headers.get("dnt") == "1":
        return

    token = body.get("token")
    if not token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing snippet token")

    try:
        token_uuid = UUID(token)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token format") from exc

    site = (await db.execute(select(Site).where(Site.snippet_token == token_uuid))).scalar_one_or_none()
    if not site:
        return

    viewport = body.get("viewport_width")
    try:
        viewport_int = int(viewport) if viewport is not None else None
    except (TypeError, ValueError):
        viewport_int = None

    db.add(
        SnippetEvent(
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
            inp_ms=_safe_int(body.get("inp")),
            fcp_ms=_safe_int(body.get("fcp")),
            device_type=_detect_device(user_agent, viewport_int),
            user_agent=user_agent,
            viewport_width=viewport_int,
        )
    )
    await db.commit()
