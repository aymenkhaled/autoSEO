"""Snippet router — receives beacon data from the JS snippet (Layer 4)."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from dependencies import get_db
from schemas.issue import SnippetEventCreate
from models.tables import Site, SnippetEvent

router = APIRouter(tags=["snippet"])


@router.post("/collect", status_code=status.HTTP_204_NO_CONTENT)
async def collect_snippet_data(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive SEO data from the JS snippet installed on client sites.
    
    This endpoint is public (no auth) — authentication is via the site's
    snippet_token. The snippet sends data via navigator.sendBeacon().
    """
    try:
        body = await request.json()
    except Exception:
        # sendBeacon may send as text
        raw = await request.body()
        import json
        try:
            body = json.loads(raw)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON body",
            )

    token = body.get("token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing snippet token",
        )

    # Lookup site by snippet token
    try:
        token_uuid = UUID(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token format",
        )

    result = await db.execute(
        select(Site).where(Site.snippet_token == token_uuid)
    )
    site = result.scalar_one_or_none()
    if not site:
        # Silently ignore — don't reveal whether token exists
        return

    # Store the event
    event = SnippetEvent(
        site_id=site.id,
        org_id=site.org_id,
        page_url=body.get("url", ""),
        title=body.get("title"),
        meta_description=body.get("meta_description"),
        canonical_url=body.get("canonical"),
        h1_text=body.get("h1"),
        schema_json=body.get("schema"),
        lcp_ms=body.get("lcp"),
        cls_score=body.get("cls"),
        ttfb_ms=body.get("ttfb"),
        user_agent=request.headers.get("user-agent"),
        viewport_width=body.get("viewport_width"),
    )
    db.add(event)
    await db.commit()
