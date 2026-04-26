"""Keywords router — keyword tracking and ranking history."""
import csv
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from config import get_settings
from dependencies import get_db, get_current_user
from schemas.auth import AuthContext
from models.tables import Keyword, KeywordProviderSyncRun, KeywordRanking, SearchConsoleQueryMetric, Site
from packages.shared.readiness import READINESS_TRACKING_ONLY, READINESS_UNAVAILABLE_WITHOUT_PROVIDER, readiness_payload

router = APIRouter(tags=["keywords"])
settings = get_settings()


class KeywordCreate(BaseModel):
    site_id: UUID
    keyword: str
    target_url: Optional[str] = None
    intent: str = "informational"
    priority: int = 1


class KeywordImportRequest(BaseModel):
    site_id: UUID
    csv_text: str


class KeywordProviderSyncRequest(BaseModel):
    site_id: UUID
    provider: str = "dataforseo"


class KeywordResponse(BaseModel):
    id: UUID
    site_id: UUID
    keyword: str
    target_url: Optional[str]
    intent: str
    priority: int
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("")
async def list_keywords(
    site_id: UUID = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all tracked keywords for a site."""
    result = await db.execute(
        select(Keyword)
        .where(Keyword.site_id == site_id, Keyword.org_id == auth.org_id)
        .order_by(Keyword.priority.desc(), Keyword.created_at.desc())
    )
    keywords = result.scalars().all()

    # Get latest rankings for each keyword
    kw_list = []
    for kw in keywords:
        latest_ranking = (await db.execute(
            select(KeywordRanking)
            .where(KeywordRanking.keyword_id == kw.id)
            .order_by(KeywordRanking.checked_at.desc())
            .limit(1)
        )).scalar_one_or_none()

        kw_list.append({
            "id": str(kw.id),
            "keyword": kw.keyword,
            "target_url": kw.target_url,
            "intent": kw.intent,
            "priority": kw.priority,
            "created_at": kw.created_at.isoformat() if kw.created_at else None,
            "latest_ranking": {
                "position": latest_ranking.position,
                "previous_position": latest_ranking.previous_position,
                "search_volume": latest_ranking.search_volume,
                "url": latest_ranking.url,
                "checked_at": latest_ranking.checked_at.isoformat() if latest_ranking.checked_at else None,
            } if latest_ranking else None,
        })
    return {
        "keywords": kw_list,
        "total": len(kw_list),
        "readiness": readiness_payload(
            READINESS_TRACKING_ONLY,
            label="Tracking only",
            description="Keywords are stored by site, intent, and priority. Ranking history stays empty until a SERP provider or manual import is connected.",
        ),
        "provider_gap": readiness_payload(
            READINESS_UNAVAILABLE_WITHOUT_PROVIDER,
            label="Ranking data missing",
            description="Live rankings, search volume, and SERP features still need an external ranking data source.",
        ),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_keyword(
    data: KeywordCreate,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a keyword to track."""
    kw = Keyword(
        org_id=auth.org_id,
        site_id=data.site_id,
        keyword=data.keyword,
        target_url=data.target_url,
        intent=data.intent,
        priority=data.priority,
        added_by=auth.user_id,
    )
    db.add(kw)
    await db.commit()
    await db.refresh(kw)
    return {"id": str(kw.id), "keyword": kw.keyword, "message": "Keyword added for tracking"}


@router.post("/import")
async def import_keyword_rankings(
    data: KeywordImportRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Import manual keyword ranking CSV data."""
    reader = csv.DictReader(StringIO(data.csv_text.strip()))
    fieldnames = {name.strip().lower() for name in (reader.fieldnames or [])}
    if "keyword" not in fieldnames:
        raise HTTPException(status_code=400, detail="CSV must include a keyword column")

    created_keywords = 0
    created_rankings = 0
    errors: list[dict] = []
    existing = {
        row.keyword.lower(): row
        for row in (
            await db.execute(
                select(Keyword).where(Keyword.site_id == data.site_id, Keyword.org_id == auth.org_id)
            )
        ).scalars().all()
    }

    def get_value(row: dict, *names: str) -> str:
        normalized = {str(k).strip().lower(): v for k, v in row.items()}
        for name in names:
            value = normalized.get(name)
            if value not in (None, ""):
                return str(value).strip()
        return ""

    def to_int(value: str) -> int | None:
        try:
            return int(float(value)) if value else None
        except ValueError:
            return None

    for index, row in enumerate(reader, start=2):
        keyword_text = get_value(row, "keyword", "query")
        if not keyword_text:
            errors.append({"row": index, "error": "Missing keyword"})
            continue

        keyword = existing.get(keyword_text.lower())
        if not keyword:
            keyword = Keyword(
                org_id=auth.org_id,
                site_id=data.site_id,
                keyword=keyword_text,
                target_url=get_value(row, "target_url", "url") or None,
                intent=get_value(row, "intent") or "informational",
                priority=to_int(get_value(row, "priority")) or 1,
                added_by=auth.user_id,
            )
            db.add(keyword)
            await db.flush()
            existing[keyword_text.lower()] = keyword
            created_keywords += 1

        checked_at = datetime.now(timezone.utc)
        date_value = get_value(row, "date", "checked_at")
        if date_value:
            try:
                checked_at = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
            except ValueError:
                errors.append({"row": index, "error": f"Invalid date '{date_value}', used import time"})

        db.add(KeywordRanking(
            keyword_id=keyword.id,
            site_id=data.site_id,
            org_id=auth.org_id,
            position=to_int(get_value(row, "position", "rank")),
            previous_position=to_int(get_value(row, "previous_position", "previous_rank", "prev_position")),
            search_volume=to_int(get_value(row, "volume", "search_volume")),
            cpc_usd=None,
            difficulty=to_int(get_value(row, "difficulty")),
            url=get_value(row, "url", "ranking_url", "target_url") or keyword.target_url,
            serp_features=[item.strip() for item in get_value(row, "serp_features").split("|") if item.strip()] or None,
            country=get_value(row, "country") or "US",
            device=get_value(row, "device") or "desktop",
            checked_at=checked_at,
        ))
        created_rankings += 1

    await db.commit()
    return {
        "site_id": str(data.site_id),
        "keywords_created": created_keywords,
        "rankings_created": created_rankings,
        "errors": errors[:20],
        "message": "Manual ranking import completed. Live rank tracking still requires a SERP provider.",
    }


@router.post("/sync-provider")
async def sync_keyword_provider(
    data: KeywordProviderSyncRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a provider sync attempt and refuse fake data when credentials are absent."""
    site = (
        await db.execute(select(Site).where(Site.id == data.site_id, Site.org_id == auth.org_id))
    ).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    provider = data.provider.lower().strip()
    configured = (
        provider == "dataforseo" and bool(settings.DATAFORSEO_LOGIN and settings.DATAFORSEO_PASSWORD)
    ) or (
        provider == "serpapi" and bool(settings.SERPAPI_API_KEY)
    )
    status_value = "provider_not_wired"
    message = (
        f"{provider} credentials are configured, but the live rank-sync worker is not implemented yet. Use CSV import until provider sync is wired."
        if configured
        else f"{provider} credentials are missing, so AutoSEO did not invent rankings. Use CSV import until a SERP provider is connected."
    )
    run = KeywordProviderSyncRun(
        org_id=auth.org_id,
        site_id=site.id,
        provider=provider,
        status=status_value,
        keywords_synced=0,
        message=message,
        data={"configured": configured, "site_domain": site.domain},
        created_by=auth.user_id,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return {
        "id": str(run.id),
        "site_id": str(site.id),
        "provider": provider,
        "status": run.status,
        "keywords_synced": run.keywords_synced,
        "configured": configured,
        "message": message,
    }


@router.post("/sync-provider/run", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def run_keyword_provider_sync(
    data: KeywordProviderSyncRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reserve the real provider-sync route without pretending the job exists."""
    site = (
        await db.execute(select(Site).where(Site.id == data.site_id, Site.org_id == auth.org_id))
    ).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "status": "provider_not_wired",
            "provider": data.provider.lower().strip(),
            "message": "Live SERP provider sync is not implemented yet. Use CSV ranking import for now.",
        },
    )


@router.get("/opportunities")
async def keyword_opportunities(
    site_id: UUID = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    keywords = (
        await db.execute(
            select(Keyword)
            .where(Keyword.site_id == site_id, Keyword.org_id == auth.org_id)
            .order_by(Keyword.priority.desc(), Keyword.created_at.desc())
        )
    ).scalars().all()
    opportunities = []
    for keyword in keywords:
        latest = (
            await db.execute(
                select(KeywordRanking)
                .where(KeywordRanking.keyword_id == keyword.id)
                .order_by(KeywordRanking.checked_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if latest and latest.position and 4 <= latest.position <= 20:
            opportunities.append({
                "type": "striking_distance_keyword",
                "keyword": keyword.keyword,
                "target_url": latest.url or keyword.target_url,
                "position": latest.position,
                "previous_position": latest.previous_position,
                "search_volume": latest.search_volume,
                "priority_score": 180 + max(0, 20 - latest.position),
                "next_step": "Refresh the target page, improve title/meta intent match, and add internal links.",
            })
        elif not latest:
            opportunities.append({
                "type": "keyword_missing_rank_data",
                "keyword": keyword.keyword,
                "target_url": keyword.target_url,
                "priority_score": 50 + int(keyword.priority or 1) * 10,
                "next_step": "Import CSV rankings or connect a SERP provider before using this keyword for proof-based decisions.",
            })

    gsc_queries = (
        await db.execute(
            select(
                SearchConsoleQueryMetric.query,
                SearchConsoleQueryMetric.page_url,
                SearchConsoleQueryMetric.impressions,
                SearchConsoleQueryMetric.clicks,
                SearchConsoleQueryMetric.ctr,
                SearchConsoleQueryMetric.position,
            )
            .where(SearchConsoleQueryMetric.site_id == site_id, SearchConsoleQueryMetric.org_id == auth.org_id)
            .order_by(SearchConsoleQueryMetric.impressions.desc())
            .limit(50)
        )
    ).all()
    tracked = {kw.keyword.lower() for kw in keywords}
    for query, page_url, impressions, clicks, ctr, position in gsc_queries:
        if query.lower() in tracked:
            continue
        if float(impressions or 0) >= 100:
            opportunities.append({
                "type": "gsc_query_not_tracked",
                "keyword": query,
                "target_url": page_url,
                "impressions": float(impressions or 0),
                "clicks": float(clicks or 0),
                "ctr": float(ctr or 0),
                "position": float(position or 0),
                "priority_score": min(220, 100 + int(float(impressions or 0) / 100)),
                "next_step": "Add this Search Console query as a tracked keyword and map it to the best landing page.",
            })

    opportunities.sort(key=lambda item: item.get("priority_score", 0), reverse=True)
    return {
        "site_id": str(site_id),
        "opportunities": opportunities[:50],
        "total": len(opportunities),
        "message": "Keyword opportunities combine manual ranking imports with Search Console queries. Live SERP features require DataForSEO or SerpApi.",
    }


@router.delete("/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyword(
    keyword_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a keyword from tracking."""
    result = await db.execute(
        select(Keyword).where(Keyword.id == keyword_id, Keyword.org_id == auth.org_id)
    )
    kw = result.scalar_one_or_none()
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    await db.delete(kw)
    await db.commit()


@router.get("/{keyword_id}/history")
async def get_keyword_history(
    keyword_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get ranking history for a specific keyword."""
    kw = (await db.execute(
        select(Keyword).where(Keyword.id == keyword_id, Keyword.org_id == auth.org_id)
    )).scalar_one_or_none()
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")

    result = await db.execute(
        select(KeywordRanking)
        .where(KeywordRanking.keyword_id == keyword_id)
        .order_by(KeywordRanking.checked_at.desc())
        .limit(90)
    )
    rankings = result.scalars().all()
    return {
        "keyword": kw.keyword,
        "history": [
            {
                "position": r.position,
                "previous_position": r.previous_position,
                "search_volume": r.search_volume,
                "url": r.url,
                "checked_at": r.checked_at.isoformat() if r.checked_at else None,
            }
            for r in rankings
        ],
    }
