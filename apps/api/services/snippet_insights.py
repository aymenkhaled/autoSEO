"""Runtime snippet insight generation."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from math import ceil
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.tables import Page, Site, SnippetEvent, SnippetInsight


THRESHOLDS = {
    "lcp_ms": ("Largest Contentful Paint is slow", 2500, "high"),
    "inp_ms": ("Interaction to Next Paint is slow", 200, "high"),
    "cls_score": ("Cumulative Layout Shift is high", 0.1, "medium"),
    "fcp_ms": ("First Contentful Paint is slow", 1800, "medium"),
    "ttfb_ms": ("Server response time is slow", 800, "medium"),
}


def p75(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, ceil(len(ordered) * 0.75) - 1)
    return ordered[index]


def _float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


async def compute_snippet_insights(db: AsyncSession, *, site: Site) -> dict[str, Any]:
    events = (
        await db.execute(
            select(SnippetEvent)
            .where(SnippetEvent.site_id == site.id, SnippetEvent.org_id == site.org_id)
            .order_by(SnippetEvent.created_at.desc())
            .limit(2000)
        )
    ).scalars().all()
    if not events:
        return {
            "status": "no_data",
            "events_analyzed": 0,
            "insights": [],
            "message": "Install the snippet and wait for real visitor events before runtime insights appear.",
        }

    pages = (
        await db.execute(
            select(Page)
            .where(Page.site_id == site.id, Page.org_id == site.org_id)
            .order_by(Page.created_at.desc())
        )
    ).scalars().all()
    page_by_url = {page.url.rstrip("/"): page for page in pages}

    grouped: dict[tuple[str, str], list[SnippetEvent]] = defaultdict(list)
    for event in events:
        grouped[(event.page_url.rstrip("/"), event.device_type or "unknown")].append(event)

    insights: list[dict[str, Any]] = []
    for (page_url, device), rows in grouped.items():
        for metric, (title, threshold, severity) in THRESHOLDS.items():
            values = [_float(getattr(row, metric)) for row in rows]
            clean = [value for value in values if value is not None]
            metric_p75 = p75(clean)
            if len(clean) >= 3 and metric_p75 > threshold:
                insights.append({
                    "source": "snippet",
                    "type": f"runtime_{metric}_p75",
                    "title": title,
                    "description": f"P75 {metric.replace('_', ' ')} is {round(metric_p75, 2)} on {device}; threshold is {threshold}.",
                    "severity": severity,
                    "page_url": page_url,
                    "device_type": device,
                    "metric_name": metric,
                    "metric_value": round(metric_p75, 3),
                    "sample_size": len(clean),
                    "priority_score": 85 if severity == "high" else 60,
                })

        latest = rows[0]
        page = page_by_url.get(page_url)
        if page and latest.title and page.title and latest.title.strip() != page.title.strip():
            insights.append({
                "source": "snippet",
                "type": "rendered_title_differs_from_crawl",
                "title": "Rendered title differs from crawler title",
                "description": "The installed snippet sees a different title after JavaScript renders than the crawler stored in the last crawl.",
                "severity": "medium",
                "page_url": page_url,
                "device_type": device,
                "metric_name": "title",
                "metric_value": None,
                "sample_size": len(rows),
                "priority_score": 70,
                "data": {"crawler_title": page.title, "rendered_title": latest.title},
            })
        if page and latest.meta_description and page.meta_description and latest.meta_description.strip() != page.meta_description.strip():
            insights.append({
                "source": "snippet",
                "type": "rendered_meta_differs_from_crawl",
                "title": "Rendered meta description differs from crawler meta",
                "description": "JavaScript changes the meta description after load; crawlers may see a different search snippet than users.",
                "severity": "medium",
                "page_url": page_url,
                "device_type": device,
                "metric_name": "meta_description",
                "metric_value": None,
                "sample_size": len(rows),
                "priority_score": 65,
                "data": {"crawler_meta": page.meta_description, "rendered_meta": latest.meta_description},
            })

    insights.sort(key=lambda item: item["priority_score"], reverse=True)
    return {
        "status": "ready",
        "events_analyzed": len(events),
        "insights": insights[:25],
        "message": "Runtime snippet insights use bot-filtered collected events and P75 Core Web Vitals thresholds.",
    }


async def persist_snippet_insights(db: AsyncSession, *, site: Site) -> dict[str, Any]:
    payload = await compute_snippet_insights(db, site=site)
    if payload["status"] != "ready":
        return payload
    for item in payload["insights"]:
        db.add(SnippetInsight(
            org_id=site.org_id,
            site_id=site.id,
            page_url=item.get("page_url"),
            insight_type=item["type"],
            severity=item.get("severity") or "medium",
            device_type=item.get("device_type"),
            metric_name=item.get("metric_name"),
            metric_value=item.get("metric_value"),
            sample_size=item.get("sample_size") or 0,
            title=item["title"],
            description=item.get("description"),
            data=item.get("data") or item,
        ))
    await db.flush()
    return payload
