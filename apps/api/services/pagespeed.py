"""PageSpeed Insights and CrUX helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from models.tables import Page, PageSpeedRun, Site
from packages.crawler.url_utils import is_safe_url

PAGESPEED_API = "https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed"
CRUX_API = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"


def pagespeed_available(settings: Settings) -> bool:
    # PageSpeed works without a key, but an API key raises quota and makes the
    # production setup explicit.
    return True


def _score(category: dict | None) -> int | None:
    if not category or category.get("score") is None:
        return None
    return int(round(float(category["score"]) * 100))


def _audit_numeric(audits: dict, key: str) -> int | None:
    value = (audits.get(key) or {}).get("numericValue")
    if value is None:
        return None
    return int(round(float(value)))


def _first_audit_numeric(audits: dict, keys: list[str]) -> int | None:
    for key in keys:
        value = _audit_numeric(audits, key)
        if value is not None:
            return value
    return None


def _cls(audits: dict) -> float | None:
    value = (audits.get("cumulative-layout-shift") or {}).get("numericValue")
    if value is None:
        return None
    return round(float(value), 4)


def _opportunity_rows(audits: dict) -> list[dict[str, Any]]:
    out = []
    for key, audit in audits.items():
        details = audit.get("details") or {}
        if details.get("type") != "opportunity":
            continue
        savings = audit.get("numericValue") or details.get("overallSavingsMs") or 0
        out.append({
            "id": key,
            "title": audit.get("title"),
            "description": audit.get("description"),
            "score": audit.get("score"),
            "estimated_savings_ms": int(round(float(savings or 0))),
        })
    return sorted(out, key=lambda item: item["estimated_savings_ms"], reverse=True)[:12]


def _diagnostic_rows(audits: dict) -> list[dict[str, Any]]:
    keys = [
        "render-blocking-resources",
        "unused-javascript",
        "unused-css-rules",
        "modern-image-formats",
        "uses-optimized-images",
        "uses-responsive-images",
        "server-response-time",
        "third-party-summary",
    ]
    return [
        {
            "id": key,
            "title": (audits.get(key) or {}).get("title"),
            "score": (audits.get(key) or {}).get("score"),
            "display_value": (audits.get(key) or {}).get("displayValue"),
        }
        for key in keys
        if key in audits
    ]


def _extract_crux_metric(crux: dict, metric: str) -> dict | None:
    item = ((crux.get("record") or {}).get("metrics") or {}).get(metric)
    if not item:
        return None
    return {
        "p75": (item.get("percentiles") or {}).get("p75"),
        "histogram": item.get("histogram") or [],
    }


async def _query_crux(settings: Settings, *, url: str, strategy: str) -> dict:
    params = {"key": settings.GOOGLE_CRUX_API_KEY} if settings.GOOGLE_CRUX_API_KEY else None
    form_factor = "PHONE" if strategy == "mobile" else "DESKTOP"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                CRUX_API,
                params=params,
                json={
                    "url": url,
                    "formFactor": form_factor,
                    "metrics": [
                        "largest_contentful_paint",
                        "interaction_to_next_paint",
                        "cumulative_layout_shift",
                        "first_contentful_paint",
                        "experimental_time_to_first_byte",
                    ],
                },
            )
        if response.status_code == 404:
            return {"available": False, "message": "CrUX has no URL-level field data for this page yet."}
        response.raise_for_status()
        data = response.json()
        return {
            "available": True,
            "lcp": _extract_crux_metric(data, "largest_contentful_paint"),
            "inp": _extract_crux_metric(data, "interaction_to_next_paint"),
            "cls": _extract_crux_metric(data, "cumulative_layout_shift"),
            "fcp": _extract_crux_metric(data, "first_contentful_paint"),
            "ttfb": _extract_crux_metric(data, "experimental_time_to_first_byte"),
        }
    except Exception as exc:
        return {"available": False, "message": str(exc)[:300]}


async def run_pagespeed_check(
    db: AsyncSession,
    settings: Settings,
    *,
    site: Site,
    url: str,
    strategy: str = "mobile",
) -> PageSpeedRun:
    strategy = strategy if strategy in {"mobile", "desktop"} else "mobile"
    if not is_safe_url(url):
        run = PageSpeedRun(
            org_id=site.org_id,
            site_id=site.id,
            page_url=url,
            strategy=strategy,
            status="failed",
            error_message="URL failed SSRF-safe validation.",
            checked_at=datetime.now(timezone.utc),
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)
        return run

    run = PageSpeedRun(
        org_id=site.org_id,
        site_id=site.id,
        page_url=url,
        strategy=strategy,
        status="running",
        checked_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.flush()
    try:
        params: dict[str, Any] = {
            "url": url,
            "strategy": strategy,
            "category": ["performance", "accessibility", "best-practices", "seo"],
        }
        if settings.GOOGLE_PAGESPEED_API_KEY:
            params["key"] = settings.GOOGLE_PAGESPEED_API_KEY
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(PAGESPEED_API, params=params)
        response.raise_for_status()
        payload = response.json()
        lighthouse = payload.get("lighthouseResult") or {}
        categories = lighthouse.get("categories") or {}
        audits = lighthouse.get("audits") or {}
        crux = await _query_crux(settings, url=url, strategy=strategy)

        run.status = "completed"
        run.performance_score = _score(categories.get("performance"))
        run.accessibility_score = _score(categories.get("accessibility"))
        run.best_practices_score = _score(categories.get("best-practices"))
        run.seo_score = _score(categories.get("seo"))
        run.lcp_ms = _audit_numeric(audits, "largest-contentful-paint")
        run.inp_ms = _first_audit_numeric(audits, ["interaction-to-next-paint", "experimental-interaction-to-next-paint", "interactive"])
        run.cls_score = _cls(audits)
        run.fcp_ms = _audit_numeric(audits, "first-contentful-paint")
        run.ttfb_ms = _audit_numeric(audits, "server-response-time")
        run.total_blocking_time_ms = _audit_numeric(audits, "total-blocking-time")
        run.speed_index_ms = _audit_numeric(audits, "speed-index")
        run.opportunities = _opportunity_rows(audits)
        run.diagnostics = _diagnostic_rows(audits)
        run.crux_metrics = crux
        run.screenshot = (((audits.get("final-screenshot") or {}).get("details") or {}).get("data"))
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)[:1000]
    await db.commit()
    await db.refresh(run)
    return run


async def default_pages_for_site(db: AsyncSession, *, site: Site, limit: int = 3) -> list[str]:
    rows = (
        await db.execute(
            select(Page.url)
            .where(Page.site_id == site.id, Page.org_id == site.org_id)
            .order_by(Page.seo_score.asc().nullslast(), Page.created_at.desc())
            .limit(max(1, min(limit, 10)))
        )
    ).all()
    urls = [row[0] for row in rows if row[0]]
    return urls or [site.domain]
