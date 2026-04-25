"""Opportunity generation across crawl, GSC, snippet, and GitHub signals."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.tables import Issue, Page, SearchConsoleInspection, SearchConsolePageMetric, Site, SiteOpportunity
from packages.shared.priority_engine import GscImpact, score_group
from packages.shared.readiness import connection_status_payload
from packages.shared.seo_domain import issue_is_auto_fixable
from services.snippet_insights import compute_snippet_insights


async def page_gsc_impact(db: AsyncSession, *, site: Site) -> dict[str, GscImpact]:
    rows = (
        await db.execute(
            select(
                SearchConsolePageMetric.page_url,
                func.sum(SearchConsolePageMetric.impressions),
                func.sum(SearchConsolePageMetric.clicks),
                func.avg(SearchConsolePageMetric.ctr),
                func.avg(SearchConsolePageMetric.position),
            )
            .where(SearchConsolePageMetric.site_id == site.id, SearchConsolePageMetric.org_id == site.org_id)
            .group_by(SearchConsolePageMetric.page_url)
        )
    ).all()
    return {
        page_url: GscImpact(
            impressions=float(impressions or 0),
            clicks=float(clicks or 0),
            ctr=float(ctr or 0),
            position=float(position or 0),
        )
        for page_url, impressions, clicks, ctr, position in rows
    }


async def issue_priorities(db: AsyncSession, *, site: Site, fix_status: str = "pending") -> list[dict[str, Any]]:
    page_impact = await page_gsc_impact(db, site=site)
    connection = connection_status_payload(site)
    rows = (
        await db.execute(
            select(Issue, Page.url)
            .join(Page, Issue.page_id == Page.id, isouter=True)
            .where(Issue.site_id == site.id, Issue.org_id == site.org_id, Issue.fix_status == fix_status)
            .order_by(Issue.impact_score.desc())
        )
    ).all()
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for issue, page_url in rows:
        key = (issue.type, issue.category)
        group = grouped.setdefault(
            key,
            {
                "type": issue.type,
                "category": issue.category,
                "severity": issue.severity,
                "affected_count": 0,
                "total_impact": 0,
                "sample_urls": [],
                "gsc": GscImpact(),
            },
        )
        group["affected_count"] += 1
        group["total_impact"] += issue.impact_score or 0
        if page_url and len(group["sample_urls"]) < 8:
            group["sample_urls"].append(page_url)
        if page_url in page_impact:
            current = group["gsc"]
            extra = page_impact[page_url]
            group["gsc"] = GscImpact(
                impressions=current.impressions + extra.impressions,
                clicks=current.clicks + extra.clicks,
                ctr=max(current.ctr, extra.ctr),
                position=extra.position or current.position,
            )

    out = []
    fix_ready = bool(connection.get("auto_deploy_capable") and connection.get("write_integration_configured"))
    for group in grouped.values():
        score = score_group(
            severity=group["severity"],
            total_impact=group["total_impact"],
            affected_count=group["affected_count"],
            fix_ready=fix_ready or issue_is_auto_fixable(group["type"]),
            gsc=group["gsc"],
        )
        out.append({**{k: v for k, v in group.items() if k != "gsc"}, **score})
    return sorted(out, key=lambda item: item["priority_score"], reverse=True)


async def site_opportunities(db: AsyncSession, *, site: Site) -> dict[str, Any]:
    opportunities: list[dict[str, Any]] = []
    page_metrics = (
        await db.execute(
            select(SearchConsolePageMetric)
            .where(SearchConsolePageMetric.site_id == site.id, SearchConsolePageMetric.org_id == site.org_id)
            .order_by(SearchConsolePageMetric.impressions.desc())
            .limit(100)
        )
    ).scalars().all()

    seen = set()
    for metric in page_metrics:
        key = ("gsc", metric.page_url)
        if key in seen:
            continue
        seen.add(key)
        impressions = float(metric.impressions or 0)
        ctr = float(metric.ctr or 0)
        position = float(metric.position or 0)
        if impressions >= 100 and ctr < 0.03:
            opportunities.append({
                "source": "gsc",
                "type": "high_impressions_low_ctr",
                "title": "High impressions but weak CTR",
                "description": "Google is showing this page, but searchers are not clicking enough. Improve title/meta relevance before chasing more pages.",
                "affected_url": metric.page_url,
                "priority_score": min(290, 140 + int(impressions / 100)),
                "impact_label": "CTR opportunity",
                "data": {"clicks": float(metric.clicks or 0), "impressions": impressions, "ctr": ctr, "position": position},
            })
        if 4 <= position <= 20 and impressions >= 50:
            opportunities.append({
                "source": "gsc",
                "type": "striking_distance_query_page",
                "title": "Ranking within striking distance",
                "description": "This page already ranks near page one. Improve content depth, titles, internal links, and schema before lower-impact fixes.",
                "affected_url": metric.page_url,
                "priority_score": min(260, 120 + int(impressions / 150)),
                "impact_label": "Ranking opportunity",
                "data": {"clicks": float(metric.clicks or 0), "impressions": impressions, "ctr": ctr, "position": position},
            })

    crawl_pages = {
        row[0].rstrip("/")
        for row in (
            await db.execute(select(Page.url).where(Page.site_id == site.id, Page.org_id == site.org_id))
        ).all()
    }
    for metric in page_metrics[:50]:
        if metric.page_url.rstrip("/") not in crawl_pages and float(metric.impressions or 0) >= 20:
            opportunities.append({
                "source": "gsc",
                "type": "gsc_page_missing_from_crawl",
                "title": "Google sees a page AutoSEO did not crawl",
                "description": "This page receives Google visibility but was not in the latest crawl set. Increase crawl coverage or check sitemap/internal links.",
                "affected_url": metric.page_url,
                "priority_score": 115,
                "impact_label": "Coverage gap",
                "data": {"impressions": float(metric.impressions or 0), "clicks": float(metric.clicks or 0)},
            })

    inspections = (
        await db.execute(
            select(SearchConsoleInspection)
            .where(SearchConsoleInspection.site_id == site.id, SearchConsoleInspection.org_id == site.org_id)
            .order_by(SearchConsoleInspection.created_at.desc())
            .limit(25)
        )
    ).scalars().all()
    for item in inspections:
        verdict = (item.verdict or "").upper()
        if verdict and verdict not in {"PASS", "VERDICT_UNSPECIFIED"}:
            opportunities.append({
                "source": "gsc",
                "type": "url_inspection_warning",
                "title": "Google URL inspection warning",
                "description": item.coverage_state or "Google reported an indexing or coverage warning for this URL.",
                "affected_url": item.url,
                "priority_score": 180,
                "impact_label": "Indexing risk",
                "data": {"verdict": item.verdict, "indexing_state": item.indexing_state, "page_fetch_state": item.page_fetch_state},
            })

    snippet = await compute_snippet_insights(db, site=site)
    for insight in snippet.get("insights", [])[:10]:
        opportunities.append({
            "source": "snippet",
            "type": insight["type"],
            "title": insight["title"],
            "description": insight["description"],
            "affected_url": insight.get("page_url"),
            "priority_score": insight.get("priority_score", 60),
            "impact_label": "Runtime signal",
            "data": insight,
        })

    stored = (
        await db.execute(
            select(SiteOpportunity)
            .where(SiteOpportunity.site_id == site.id, SiteOpportunity.org_id == site.org_id, SiteOpportunity.status == "open")
            .order_by(SiteOpportunity.priority_score.desc())
            .limit(50)
        )
    ).scalars().all()
    for item in stored:
        opportunities.append({
            "source": item.source,
            "type": item.type,
            "title": item.title,
            "description": item.description,
            "affected_url": item.affected_url,
            "priority_score": item.priority_score,
            "impact_label": item.impact_label,
            "issue_type": item.issue_type,
            "data": item.data or {},
        })

    issue_items = await issue_priorities(db, site=site)
    for item in issue_items[:10]:
        opportunities.append({
            "source": "crawler",
            "type": f"fix_root_cause_{item['type']}",
            "title": item["type"].replace("_", " ").title(),
            "description": f"{item['affected_count']} affected items. Priority includes technical severity, crawl impact, GSC visibility, and fix readiness.",
            "affected_url": item["sample_urls"][0] if item["sample_urls"] else None,
            "priority_score": item["priority_score"],
            "impact_label": item["impact_label"],
            "issue_type": item["type"],
            "data": item,
        })

    opportunities.sort(key=lambda item: item.get("priority_score", 0), reverse=True)
    by_source = defaultdict(int)
    for item in opportunities:
        by_source[item["source"]] += 1

    return {
        "site_id": str(site.id),
        "opportunities": opportunities[:50],
        "total": len(opportunities),
        "by_source": dict(by_source),
        "snippet_status": snippet["status"],
        "message": "Opportunities combine crawler root causes, Search Console demand, URL inspection, and runtime snippet signals.",
    }
