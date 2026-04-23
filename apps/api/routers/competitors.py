"""Competitors router — competitor tracking and analysis."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from dependencies import get_db, get_current_user
from schemas.auth import AuthContext
from models.tables import Competitor, Crawl
from packages.crawler.url_utils import is_safe_url
from packages.shared.readiness import (
    READINESS_UNAVAILABLE_WITHOUT_PROVIDER,
    READINESS_WORKING,
    readiness_payload,
)

router = APIRouter(tags=["competitors"])


class CompetitorCreate(BaseModel):
    site_id: UUID
    domain: str
    name: Optional[str] = None


@router.get("")
async def list_competitors(
    site_id: UUID = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all tracked competitors for a site."""
    result = await db.execute(
        select(Competitor)
        .where(Competitor.site_id == site_id, Competitor.org_id == auth.org_id)
        .order_by(Competitor.created_at.desc())
    )
    competitors = result.scalars().all()
    return {
        "competitors": [
            {
                "id": str(c.id),
                "domain": c.domain,
                "name": c.name,
                "seo_score": c.seo_score,
                "keywords_count": c.keywords_count,
                "backlinks_count": c.backlinks_count,
                "last_analyzed_at": c.last_analyzed_at.isoformat() if c.last_analyzed_at else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in competitors
        ],
        "total": len(competitors),
        "readiness": readiness_payload(
            READINESS_WORKING,
            label="Lightweight crawl comparison",
            description="Competitor analysis can compare public-page SEO signals today, but deeper keyword and backlink intelligence is still limited.",
        ),
        "provider_gap": readiness_payload(
            READINESS_UNAVAILABLE_WITHOUT_PROVIDER,
            label="Provider needed for keyword/backlink data",
            description="Keyword counts and backlink counts stay unavailable until an external provider is connected.",
        ),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_competitor(
    data: CompetitorCreate,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a competitor to track."""
    domain = data.domain.lower().strip().rstrip("/")
    if domain.startswith("http://") or domain.startswith("https://"):
        from urllib.parse import urlparse
        domain = urlparse(domain).netloc

    competitor = Competitor(
        org_id=auth.org_id,
        site_id=data.site_id,
        domain=domain,
        name=data.name or domain,
        added_by=auth.user_id,
    )
    db.add(competitor)
    await db.commit()
    await db.refresh(competitor)
    return {
        "id": str(competitor.id),
        "domain": competitor.domain,
        "message": "Competitor added for tracking",
    }


@router.post("/{competitor_id}/analyze")
async def analyze_competitor(
    competitor_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run a lightweight public homepage comparison for a competitor.

    This is intentionally not a paid SERP/backlink intelligence engine yet. It
    uses the existing crawler extractor to make competitor tracking immediately
    useful while keeping the UI honest about current capability.
    """
    competitor = (
        await db.execute(
            select(Competitor).where(Competitor.id == competitor_id, Competitor.org_id == auth.org_id)
        )
    ).scalar_one_or_none()
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")

    url = competitor.domain
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    if not is_safe_url(url):
        raise HTTPException(status_code=400, detail="Competitor domain failed safety validation")

    import httpx
    from packages.crawler.extractor import SEOExtractor, calculate_page_score, classify_page_type, generate_issues

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        response = await client.get(url, headers={"User-Agent": "AutoSEO/1.0 (+https://autoseo.app)"})
    if not is_safe_url(str(response.url)):
        raise HTTPException(status_code=400, detail="Competitor redirected to an unsafe URL")

    signals = SEOExtractor(response.text, str(response.url), headers=dict(response.headers)).extract_all()
    signals["url"] = str(response.url)
    signals["status_code"] = response.status_code
    signals["page_type"] = classify_page_type(str(response.url), signals.get("schema_types"))
    signals["seo_score"] = calculate_page_score(signals)
    signals["_page_id"] = None
    issues = generate_issues([signals])

    latest_site_crawl = (
        await db.execute(
            select(Crawl)
            .where(Crawl.site_id == competitor.site_id, Crawl.org_id == auth.org_id, Crawl.status == "completed")
            .order_by(Crawl.completed_at.desc().nullslast(), Crawl.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    competitor.seo_score = signals["seo_score"]
    competitor.last_analyzed_at = datetime.utcnow()
    await db.commit()

    return {
        "id": str(competitor.id),
        "domain": competitor.domain,
        "analyzed_url": str(response.url),
        "seo_score": signals["seo_score"],
        "issue_count": len(issues),
        "title": signals.get("title"),
        "meta_description": signals.get("meta_description"),
        "schema_types": signals.get("schema_types") or [],
        "comparison": {
            "site_latest_score": latest_site_crawl.seo_score if latest_site_crawl else None,
            "score_delta_vs_site": (
                signals["seo_score"] - latest_site_crawl.seo_score
                if latest_site_crawl and latest_site_crawl.seo_score is not None
                else None
            ),
        },
        "top_issues": [
            {
                "type": issue["type"],
                "severity": issue["severity"],
                "current_value": issue.get("current_value"),
            }
            for issue in issues[:8]
        ],
        "message": "Lightweight competitor crawl completed. Keyword/backlink intelligence still requires a ranking/backlink data source.",
    }


@router.delete("/{competitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_competitor(
    competitor_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a competitor from tracking."""
    result = await db.execute(
        select(Competitor).where(Competitor.id == competitor_id, Competitor.org_id == auth.org_id)
    )
    comp = result.scalar_one_or_none()
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor not found")
    await db.delete(comp)
    await db.commit()
