"""Site Intelligence router — advanced analytical endpoints.

Endpoints
---------
GET  /sites/{site_id}/seo-score-history    — crawl-by-crawl SEO score trend
GET  /sites/{site_id}/health-trends        — per-crawl health timeseries
GET  /sites/{site_id}/orphan-pages         — pages with zero incoming internal links
GET  /sites/{site_id}/duplicate-analysis   — duplicate titles, meta descriptions, content hashes
GET  /sites/{site_id}/redirect-chains      — pages with multi-hop redirect chains
GET  /sites/{site_id}/internal-linking     — internal linking opportunities
GET  /sites/{site_id}/pagespeed-trend      — Core Web Vitals trend over time
GET  /sites/{site_id}/coverage-gaps        — crawl vs GSC page coverage gaps
GET  /sites/{site_id}/page/{page_id}       — single page detail with issues
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_current_user, get_db
from models.tables import (
    Crawl,
    Issue,
    Page,
    PageSpeedRun,
    SearchConsolePageMetric,
    Site,
)
from schemas.auth import AuthContext

router = APIRouter(tags=["site-intelligence"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_site(db: AsyncSession, site_id: UUID, org_id: UUID) -> Site:
    site = (
        await db.execute(select(Site).where(Site.id == site_id, Site.org_id == org_id))
    ).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


async def _latest_completed_crawl_id(db: AsyncSession, site_id: UUID, org_id: UUID) -> UUID | None:
    return (
        await db.execute(
            select(Crawl.id)
            .where(Crawl.site_id == site_id, Crawl.org_id == org_id, Crawl.status == "completed")
            .order_by(Crawl.completed_at.desc().nullslast(), Crawl.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


# ---------------------------------------------------------------------------
# 1. SEO Score History
# ---------------------------------------------------------------------------

@router.get("/{site_id}/seo-score-history")
async def get_seo_score_history(
    site_id: UUID,
    limit: int = Query(30, ge=1, le=90),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return crawl-by-crawl SEO score trend for a site."""
    await _get_site(db, site_id, auth.org_id)

    rows = (
        await db.execute(
            select(
                Crawl.id,
                Crawl.seo_score,
                Crawl.pages_crawled,
                Crawl.issues_found,
                Crawl.completed_at,
                Crawl.created_at,
            )
            .where(
                Crawl.site_id == site_id,
                Crawl.org_id == auth.org_id,
                Crawl.status == "completed",
                Crawl.seo_score.isnot(None),
            )
            .order_by(Crawl.completed_at.asc().nullslast(), Crawl.created_at.asc())
            .limit(limit)
        )
    ).all()

    history = []
    for i, row in enumerate(rows):
        prev_score = rows[i - 1][1] if i > 0 else None
        score = row[1]
        delta = (score - prev_score) if (score is not None and prev_score is not None) else None
        history.append({
            "crawl_id": str(row[0]),
            "seo_score": score,
            "delta": delta,
            "pages_crawled": row[2],
            "issues_found": row[3],
            "completed_at": row[4].isoformat() if row[4] else None,
            "created_at": row[5].isoformat() if row[5] else None,
        })

    latest_score = history[-1]["seo_score"] if history else None
    earliest_score = history[0]["seo_score"] if history else None
    total_delta = (latest_score - earliest_score) if (latest_score is not None and earliest_score is not None) else None

    return {
        "site_id": str(site_id),
        "history": history,
        "total": len(history),
        "summary": {
            "latest_score": latest_score,
            "earliest_score": earliest_score,
            "total_delta": total_delta,
            "trend": "improving" if (total_delta and total_delta > 0) else ("declining" if (total_delta and total_delta < 0) else "stable"),
        },
    }


# ---------------------------------------------------------------------------
# 2. Health Trends
# ---------------------------------------------------------------------------

@router.get("/{site_id}/health-trends")
async def get_health_trends(
    site_id: UUID,
    limit: int = Query(20, ge=1, le=60),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return per-crawl health timeseries: score, issues, pages crawled, duration."""
    await _get_site(db, site_id, auth.org_id)

    rows = (
        await db.execute(
            select(
                Crawl.id,
                Crawl.seo_score,
                Crawl.pages_crawled,
                Crawl.issues_found,
                Crawl.urls_discovered,
                Crawl.duration_ms,
                Crawl.status,
                Crawl.completed_at,
                Crawl.created_at,
            )
            .where(Crawl.site_id == site_id, Crawl.org_id == auth.org_id)
            .order_by(Crawl.created_at.desc())
            .limit(limit)
        )
    ).all()

    crawls = [
        {
            "crawl_id": str(row[0]),
            "seo_score": row[1],
            "pages_crawled": row[2] or 0,
            "issues_found": row[3] or 0,
            "urls_discovered": row[4] or 0,
            "duration_ms": row[5],
            "status": row[6],
            "completed_at": row[7].isoformat() if row[7] else None,
            "created_at": row[8].isoformat() if row[8] else None,
        }
        for row in reversed(rows)
    ]

    avg_score = None
    scored = [c["seo_score"] for c in crawls if c["seo_score"] is not None]
    if scored:
        avg_score = round(sum(scored) / len(scored), 1)

    return {
        "site_id": str(site_id),
        "crawls": crawls,
        "total": len(crawls),
        "summary": {
            "avg_seo_score": avg_score,
            "total_crawls": len(crawls),
            "completed_crawls": sum(1 for c in crawls if c["status"] == "completed"),
        },
    }


# ---------------------------------------------------------------------------
# 3. Orphan Pages
# ---------------------------------------------------------------------------

@router.get("/{site_id}/orphan-pages")
async def get_orphan_pages(
    site_id: UUID,
    crawl_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return pages with no internal links pointing to them (orphan pages).

    These pages cannot be discovered via normal site navigation and may
    receive no PageRank signal from the rest of the site.
    """
    await _get_site(db, site_id, auth.org_id)

    target_crawl_id = crawl_id or await _latest_completed_crawl_id(db, site_id, auth.org_id)
    if not target_crawl_id:
        return {"site_id": str(site_id), "crawl_id": None, "pages": [], "total": 0, "note": "No completed crawl found"}

    total = int(
        (
            await db.execute(
                select(func.count(Page.id)).where(
                    Page.site_id == site_id,
                    Page.crawl_id == target_crawl_id,
                    Page.incoming_links_count == 0,
                    Page.status_code == 200,
                )
            )
        ).scalar()
        or 0
    )

    rows = (
        await db.execute(
            select(Page)
            .where(
                Page.site_id == site_id,
                Page.crawl_id == target_crawl_id,
                Page.incoming_links_count == 0,
                Page.status_code == 200,
            )
            .order_by(Page.seo_score.desc().nullslast(), Page.url.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).scalars().all()

    return {
        "site_id": str(site_id),
        "crawl_id": str(target_crawl_id),
        "pages": [
            {
                "id": str(p.id),
                "url": p.url,
                "title": p.title,
                "seo_score": p.seo_score,
                "word_count": p.word_count,
                "status_code": p.status_code,
                "external_links_count": p.external_links_count or 0,
                "internal_links_count": p.internal_links_count or 0,
            }
            for p in rows
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "note": "Orphan pages are not reachable by following internal links. Add at least one internal link pointing to each orphan page to allow PageRank to flow.",
    }


# ---------------------------------------------------------------------------
# 4. Duplicate Analysis
# ---------------------------------------------------------------------------

@router.get("/{site_id}/duplicate-analysis")
async def get_duplicate_analysis(
    site_id: UUID,
    crawl_id: UUID | None = Query(None),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detect duplicate titles, meta descriptions, and content hashes across pages."""
    await _get_site(db, site_id, auth.org_id)

    target_crawl_id = crawl_id or await _latest_completed_crawl_id(db, site_id, auth.org_id)
    if not target_crawl_id:
        return {"site_id": str(site_id), "crawl_id": None, "duplicates": {}, "note": "No completed crawl found"}

    rows = (
        await db.execute(
            select(Page.url, Page.title, Page.meta_description, Page.content_hash, Page.word_count, Page.seo_score)
            .where(
                Page.site_id == site_id,
                Page.crawl_id == target_crawl_id,
                Page.status_code == 200,
            )
            .order_by(Page.url.asc())
        )
    ).all()

    title_groups: dict[str, list[str]] = defaultdict(list)
    desc_groups: dict[str, list[str]] = defaultdict(list)
    hash_groups: dict[str, list[dict]] = defaultdict(list)

    for url, title, meta_desc, content_hash, word_count, seo_score in rows:
        if title and title.strip():
            title_groups[title.strip().lower()].append(url)
        if meta_desc and meta_desc.strip():
            desc_groups[meta_desc.strip().lower()].append(url)
        if content_hash:
            hash_groups[content_hash].append({"url": url, "word_count": word_count or 0, "seo_score": seo_score})

    dup_titles = [
        {"title": t, "urls": urls, "count": len(urls)}
        for t, urls in sorted(title_groups.items(), key=lambda x: -len(x[1]))
        if len(urls) > 1
    ]
    dup_descs = [
        {"meta_description": d[:120] + "..." if len(d) > 120 else d, "urls": urls, "count": len(urls)}
        for d, urls in sorted(desc_groups.items(), key=lambda x: -len(x[1]))
        if len(urls) > 1
    ]
    dup_content = [
        {"content_hash": h, "pages": pages, "count": len(pages)}
        for h, pages in sorted(hash_groups.items(), key=lambda x: -len(x[1]))
        if len(pages) > 1
    ]

    return {
        "site_id": str(site_id),
        "crawl_id": str(target_crawl_id),
        "total_pages_analyzed": len(rows),
        "duplicates": {
            "titles": dup_titles[:30],
            "meta_descriptions": dup_descs[:30],
            "content": dup_content[:20],
        },
        "summary": {
            "duplicate_title_groups": len(dup_titles),
            "duplicate_title_pages": sum(g["count"] for g in dup_titles),
            "duplicate_meta_groups": len(dup_descs),
            "duplicate_meta_pages": sum(g["count"] for g in dup_descs),
            "duplicate_content_groups": len(dup_content),
            "duplicate_content_pages": sum(g["count"] for g in dup_content),
        },
        "note": "Duplicate titles compete for the same search intent. Duplicate meta descriptions reduce CTR differentiation. Duplicate content may cause Google to pick a non-canonical URL.",
    }


# ---------------------------------------------------------------------------
# 5. Redirect Chains
# ---------------------------------------------------------------------------

@router.get("/{site_id}/redirect-chains")
async def get_redirect_chains(
    site_id: UUID,
    crawl_id: UUID | None = Query(None),
    min_hops: int = Query(2, ge=1, le=10),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return pages involved in multi-hop redirect chains.

    Redirect chains waste crawl budget and dilute link equity.
    """
    await _get_site(db, site_id, auth.org_id)

    target_crawl_id = crawl_id or await _latest_completed_crawl_id(db, site_id, auth.org_id)
    if not target_crawl_id:
        return {"site_id": str(site_id), "crawl_id": None, "chains": [], "total": 0}

    rows = (
        await db.execute(
            select(Page.url, Page.status_code, Page.redirect_url, Page.redirect_chain, Page.response_time_ms)
            .where(
                Page.site_id == site_id,
                Page.crawl_id == target_crawl_id,
                Page.redirect_chain.isnot(None),
            )
            .order_by(Page.url.asc())
        )
    ).all()

    chains = []
    for url, status_code, redirect_url, redirect_chain, response_time_ms in rows:
        hops = redirect_chain if isinstance(redirect_chain, list) else []
        if len(hops) >= min_hops:
            chains.append({
                "url": url,
                "status_code": status_code,
                "final_url": redirect_url,
                "hops": len(hops),
                "chain": hops,
                "response_time_ms": response_time_ms,
                "recommendation": f"Update all internal links pointing to '{url}' to link directly to '{redirect_url}' to avoid the {len(hops)}-hop redirect chain.",
            })

    chains.sort(key=lambda x: -x["hops"])
    total = len(chains)
    paginated = chains[(page - 1) * per_page: page * per_page]

    return {
        "site_id": str(site_id),
        "crawl_id": str(target_crawl_id),
        "chains": paginated,
        "total": total,
        "page": page,
        "per_page": per_page,
        "summary": {
            "total_chain_pages": total,
            "max_hops": max((c["hops"] for c in chains), default=0),
            "avg_hops": round(sum(c["hops"] for c in chains) / total, 1) if total else 0,
        },
        "note": "Redirect chains (2+ hops) waste crawl budget and dilute PageRank. Update internal links to point directly to the final destination URL.",
    }


# ---------------------------------------------------------------------------
# 6. Internal Linking Opportunities
# ---------------------------------------------------------------------------

@router.get("/{site_id}/internal-linking")
async def get_internal_linking_opportunities(
    site_id: UUID,
    crawl_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(40, ge=1, le=100),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return internal linking opportunities.

    Surfaces pages that:
    - Have few incoming internal links (orphan or near-orphan)
    - Have content that could receive links from higher-traffic pages
    - Have SEO score gaps suggesting they need more link equity
    """
    await _get_site(db, site_id, auth.org_id)

    target_crawl_id = crawl_id or await _latest_completed_crawl_id(db, site_id, auth.org_id)
    if not target_crawl_id:
        return {"site_id": str(site_id), "crawl_id": None, "opportunities": [], "total": 0}

    target_pages = (
        await db.execute(
            select(Page)
            .where(
                Page.site_id == site_id,
                Page.crawl_id == target_crawl_id,
                Page.status_code == 200,
                Page.incoming_links_count < 3,
                Page.word_count > 200,
            )
            .order_by(Page.seo_score.desc().nullslast(), Page.incoming_links_count.asc())
            .limit(200)
        )
    ).scalars().all()

    source_pages = (
        await db.execute(
            select(Page)
            .where(
                Page.site_id == site_id,
                Page.crawl_id == target_crawl_id,
                Page.status_code == 200,
                Page.internal_links_count > 2,
                Page.word_count > 300,
            )
            .order_by(Page.incoming_links_count.desc().nullslast())
            .limit(50)
        )
    ).scalars().all()

    opportunities: list[dict[str, Any]] = []
    for target in target_pages:
        target_words = set((target.title or "").lower().split())
        best_sources = []
        for source in source_pages:
            if source.url == target.url:
                continue
            source_words = set((source.title or "").lower().split())
            overlap = len(target_words & source_words - {"the", "a", "an", "and", "or", "of", "to", "in", "for", "is", "it"})
            if overlap >= 1 or (target.url.split("/")[-2:-1] and any(seg in source.url for seg in target.url.split("/")[3:5] if len(seg) > 3)):
                best_sources.append({
                    "url": source.url,
                    "title": source.title,
                    "incoming_links": source.incoming_links_count or 0,
                    "word_count": source.word_count or 0,
                    "keyword_overlap": overlap,
                })

        best_sources.sort(key=lambda x: (-x["keyword_overlap"], -x["incoming_links"]))
        opportunities.append({
            "target_page": {
                "url": target.url,
                "title": target.title,
                "seo_score": target.seo_score,
                "incoming_links": target.incoming_links_count or 0,
                "word_count": target.word_count or 0,
            },
            "suggested_sources": best_sources[:5],
            "priority_score": max(0, 100 - (target.incoming_links_count or 0) * 20) + (target.seo_score or 0),
        })

    opportunities.sort(key=lambda x: -x["priority_score"])
    total = len(opportunities)
    paginated = opportunities[(page - 1) * per_page: page * per_page]

    return {
        "site_id": str(site_id),
        "crawl_id": str(target_crawl_id),
        "opportunities": paginated,
        "total": total,
        "page": page,
        "per_page": per_page,
        "note": "Pages with fewer than 3 incoming internal links may be under-valued by search engines. Add relevant internal links from higher-authority pages.",
    }


# ---------------------------------------------------------------------------
# 7. PageSpeed / CWV Trend
# ---------------------------------------------------------------------------

@router.get("/{site_id}/pagespeed-trend")
async def get_pagespeed_trend(
    site_id: UUID,
    strategy: str = Query("mobile", pattern="^(mobile|desktop)$"),
    limit: int = Query(30, ge=1, le=90),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return Core Web Vitals averages over time for a site."""
    await _get_site(db, site_id, auth.org_id)

    _day = func.date_trunc(text("'day'"), PageSpeedRun.checked_at).label("day")
    rows = (
        await db.execute(
            select(
                _day,
                func.avg(PageSpeedRun.performance_score).label("avg_performance"),
                func.avg(PageSpeedRun.lcp_ms).label("avg_lcp"),
                func.avg(PageSpeedRun.inp_ms).label("avg_inp"),
                func.avg(PageSpeedRun.cls_score).label("avg_cls"),
                func.avg(PageSpeedRun.ttfb_ms).label("avg_ttfb"),
                func.count(PageSpeedRun.id).label("pages_tested"),
            )
            .where(
                PageSpeedRun.site_id == site_id,
                PageSpeedRun.org_id == auth.org_id,
                PageSpeedRun.strategy == strategy,
                PageSpeedRun.status == "completed",
            )
            .group_by(_day)
            .order_by(_day.asc())
            .limit(limit)
        )
    ).all()

    trend = [
        {
            "day": row[0].date().isoformat() if row[0] else None,
            "avg_performance_score": round(float(row[1]), 1) if row[1] is not None else None,
            "avg_lcp_ms": round(float(row[2]), 0) if row[2] is not None else None,
            "avg_inp_ms": round(float(row[3]), 0) if row[3] is not None else None,
            "avg_cls_score": round(float(row[4]), 4) if row[4] is not None else None,
            "avg_ttfb_ms": round(float(row[5]), 0) if row[5] is not None else None,
            "pages_tested": int(row[6]) if row[6] else 0,
        }
        for row in rows
    ]

    latest = trend[-1] if trend else {}
    cwv_pass = (
        (latest.get("avg_lcp_ms") or 9999) <= 2500
        and (latest.get("avg_inp_ms") or 9999) <= 200
        and (latest.get("avg_cls_score") or 1) <= 0.1
    ) if trend else None

    return {
        "site_id": str(site_id),
        "strategy": strategy,
        "trend": trend,
        "total_days": len(trend),
        "latest": latest,
        "cwv_pass": cwv_pass,
        "thresholds": {
            "lcp_good_ms": 2500,
            "lcp_needs_improvement_ms": 4000,
            "inp_good_ms": 200,
            "inp_needs_improvement_ms": 500,
            "cls_good": 0.1,
            "cls_needs_improvement": 0.25,
        },
        "note": "Core Web Vitals are a Google ranking signal. LCP (Largest Contentful Paint) ≤ 2500ms, INP (Interaction to Next Paint) ≤ 200ms, and CLS ≤ 0.1 are the 'good' thresholds.",
    }


# ---------------------------------------------------------------------------
# 8. Coverage Gaps
# ---------------------------------------------------------------------------

@router.get("/{site_id}/coverage-gaps")
async def get_coverage_gaps(
    site_id: UUID,
    crawl_id: UUID | None = Query(None),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compare crawl coverage against Search Console data to find gaps.

    Reports:
    - Pages Google sees but AutoSEO did not crawl
    - Pages crawled but returning non-200 status
    - Pages blocked/noindex in crawl
    """
    await _get_site(db, site_id, auth.org_id)

    target_crawl_id = crawl_id or await _latest_completed_crawl_id(db, site_id, auth.org_id)
    if not target_crawl_id:
        return {"site_id": str(site_id), "crawl_id": None, "gaps": {}, "note": "No completed crawl found"}

    crawled_urls = {
        row[0].rstrip("/")
        for row in (
            await db.execute(
                select(Page.url).where(Page.site_id == site_id, Page.crawl_id == target_crawl_id)
            )
        ).all()
    }

    non_200_rows = (
        await db.execute(
            select(Page.url, Page.status_code, Page.redirect_url)
            .where(
                Page.site_id == site_id,
                Page.crawl_id == target_crawl_id,
                Page.status_code.notin_([200, None]),
            )
            .order_by(Page.status_code.asc(), Page.url.asc())
            .limit(100)
        )
    ).all()

    noindex_rows = (
        await db.execute(
            select(Page.url, Page.robots_directive)
            .where(
                Page.site_id == site_id,
                Page.crawl_id == target_crawl_id,
                Page.robots_directive.ilike("%noindex%"),
            )
            .order_by(Page.url.asc())
            .limit(100)
        )
    ).all()

    gsc_rows = (
        await db.execute(
            select(SearchConsolePageMetric.page_url, SearchConsolePageMetric.impressions, SearchConsolePageMetric.clicks)
            .where(
                SearchConsolePageMetric.site_id == site_id,
                SearchConsolePageMetric.org_id == auth.org_id,
                SearchConsolePageMetric.impressions > 5,
            )
            .order_by(SearchConsolePageMetric.impressions.desc())
            .limit(200)
        )
    ).all()

    gsc_not_crawled = [
        {
            "url": row[0],
            "impressions": float(row[1] or 0),
            "clicks": float(row[2] or 0),
        }
        for row in gsc_rows
        if row[0].rstrip("/") not in crawled_urls
    ]
    gsc_not_crawled.sort(key=lambda x: -x["impressions"])

    non_200 = [
        {"url": row[0], "status_code": row[1], "redirect_url": row[2]}
        for row in non_200_rows
    ]
    noindex = [
        {"url": row[0], "robots_directive": row[1]}
        for row in noindex_rows
    ]

    by_status: dict[int, int] = defaultdict(int)
    for item in non_200:
        by_status[item["status_code"]] += 1

    return {
        "site_id": str(site_id),
        "crawl_id": str(target_crawl_id),
        "gaps": {
            "gsc_not_crawled": gsc_not_crawled[:50],
            "non_200_pages": non_200[:50],
            "noindex_pages": noindex[:50],
        },
        "summary": {
            "total_crawled_urls": len(crawled_urls),
            "gsc_urls_not_crawled": len(gsc_not_crawled),
            "non_200_count": len(non_200),
            "noindex_count": len(noindex),
            "broken_pages": by_status.get(404, 0) + by_status.get(410, 0),
            "server_errors": by_status.get(500, 0) + by_status.get(503, 0),
            "by_status_code": dict(by_status),
        },
        "note": "Coverage gaps show differences between what Google sees and what AutoSEO crawled. GSC URLs not in the crawl may have internal linking or sitemap issues.",
    }


# ---------------------------------------------------------------------------
# 9. Single Page Detail
# ---------------------------------------------------------------------------

@router.get("/{site_id}/pages/{page_id}")
async def get_page_detail(
    site_id: UUID,
    page_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return detailed metadata and issues for a single crawled page."""
    await _get_site(db, site_id, auth.org_id)

    p = (
        await db.execute(
            select(Page).where(Page.id == page_id, Page.site_id == site_id)
        )
    ).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")

    issues = (
        await db.execute(
            select(Issue)
            .where(Issue.page_id == page_id, Issue.site_id == site_id, Issue.org_id == auth.org_id)
            .order_by(Issue.impact_score.desc())
        )
    ).scalars().all()

    return {
        "id": str(p.id),
        "crawl_id": str(p.crawl_id),
        "site_id": str(p.site_id),
        "url": p.url,
        "status_code": p.status_code,
        "redirect_url": p.redirect_url,
        "redirect_chain": p.redirect_chain,
        "crawl_depth": p.crawl_depth,
        "response_time_ms": p.response_time_ms,
        "seo_score": p.seo_score,
        "word_count": p.word_count,
        "title": p.title,
        "title_length": p.title_length,
        "meta_description": p.meta_description,
        "meta_description_length": p.meta_description_length,
        "canonical_url": p.canonical_url,
        "robots_directive": p.robots_directive,
        "h1_count": p.h1_count,
        "h1_text": p.h1_text or [],
        "h2_count": p.h2_count,
        "h3_count": p.h3_count,
        "heading_structure": p.heading_structure or {},
        "internal_links_count": p.internal_links_count or 0,
        "external_links_count": p.external_links_count or 0,
        "broken_links_count": p.broken_links_count or 0,
        "incoming_links_count": p.incoming_links_count or 0,
        "images_count": p.images_count or 0,
        "images_missing_alt": p.images_missing_alt or 0,
        "og_title": p.og_title,
        "og_description": p.og_description,
        "og_image": p.og_image,
        "twitter_card": p.twitter_card,
        "schema_types": p.schema_types or [],
        "schema_valid": p.schema_valid,
        "schema_errors": p.schema_errors or [],
        "lcp_ms": p.lcp_ms,
        "cls_score": float(p.cls_score) if p.cls_score is not None else None,
        "ttfb_ms": p.ttfb_ms,
        "performance_score": p.performance_score,
        "hreflang_tags": p.hreflang_tags or {},
        "hreflang_errors": p.hreflang_errors or [],
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "issues": [
            {
                "id": str(i.id),
                "type": i.type,
                "category": i.category,
                "severity": i.severity,
                "impact_score": i.impact_score,
                "current_value": i.current_value,
                "fix_status": i.fix_status,
                "fix_type": i.fix_type,
                "proposed_fix": i.proposed_fix,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in issues
        ],
        "issue_count": len(issues),
    }
