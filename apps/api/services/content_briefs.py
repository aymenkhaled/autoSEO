"""Content refresh brief generation and GitHub PR handoff."""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.tables import (
    AnalyticsPageMetric,
    ContentBrief,
    Page,
    SearchConsolePageMetric,
    Site,
)
from packages.ai_engine.engine import AIProviderUnavailable, generate_content_brief, is_ai_configured


async def build_content_brief_payload(
    db: AsyncSession,
    *,
    site: Site,
    page_url: str,
    target_keyword: str | None,
    title: str | None = None,
) -> dict[str, Any]:
    page = (
        await db.execute(
            select(Page)
            .where(Page.site_id == site.id, Page.org_id == site.org_id, Page.url == page_url)
            .order_by(Page.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    gsc = (
        await db.execute(
            select(
                func.sum(SearchConsolePageMetric.clicks),
                func.sum(SearchConsolePageMetric.impressions),
                func.avg(SearchConsolePageMetric.ctr),
                func.avg(SearchConsolePageMetric.position),
            ).where(
                SearchConsolePageMetric.site_id == site.id,
                SearchConsolePageMetric.org_id == site.org_id,
                SearchConsolePageMetric.page_url == page_url,
            )
        )
    ).one()
    ga = (
        await db.execute(
            select(
                func.sum(AnalyticsPageMetric.sessions),
                func.sum(AnalyticsPageMetric.key_events),
                func.sum(AnalyticsPageMetric.total_revenue),
            ).where(
                AnalyticsPageMetric.site_id == site.id,
                AnalyticsPageMetric.org_id == site.org_id,
                AnalyticsPageMetric.page_url == page_url,
            )
        )
    ).one()

    keyword = target_keyword or (page.title if page and page.title else site.name)
    brief_title = title or f"Refresh {keyword} page for stronger search and AI visibility"
    current_title = page.title if page else None
    current_meta = page.meta_description if page else None
    word_count = page.word_count if page else None
    clicks = float(gsc[0] or 0)
    impressions = float(gsc[1] or 0)
    ctr = float(gsc[2] or 0)
    position = float(gsc[3] or 0)
    sessions = float(ga[0] or 0)
    key_events = float(ga[1] or 0)
    revenue = float(ga[2] or 0)

    generation_mode = "deterministic_fallback"
    ai_notes = None
    ai_error = None
    ai_outline = None
    ai_suggested_word_count = None
    ai_tone = None
    if is_ai_configured():
        try:
            ai_brief = await generate_content_brief(keyword=keyword, domain=site.domain)
            generation_mode = "ai_anthropic"
            brief_title = title or ai_brief.title
            ai_outline = ai_brief.outline
            ai_suggested_word_count = ai_brief.suggested_word_count
            ai_tone = ai_brief.tone
            ai_notes = ai_brief.notes
        except AIProviderUnavailable:
            generation_mode = "deterministic_fallback"
        except Exception as exc:
            generation_mode = "ai_failed_fallback"
            ai_error = str(exc)[:300]

    fallback_sections = [
        f"Direct answer: what is {keyword} and who it is for",
        "Proof points: outcomes, screenshots, customer evidence, or data",
        "Comparison / alternatives section for decision-stage searches",
        "FAQ section using only questions the page can answer honestly",
        "Clear next-step CTA above the fold and after the main proof section",
    ]
    recommended_sections = ai_outline or fallback_sections
    metadata_variants = [
        {
            "title": f"{keyword}: Practical Guide, Examples, and Next Steps",
            "meta_description": f"Learn how {keyword} works, what to fix first, and the next action to take. Built from AutoSEO crawl, GSC, and GA4 signals.",
        },
        {
            "title": f"Improve {keyword} Results With a Proof-Driven SEO Workflow",
            "meta_description": f"Use real search and conversion data to prioritize {keyword} improvements, update content, and prove impact after deploy.",
        },
    ]
    schema_suggestions = [
        "Article schema if this is an educational page.",
        "FAQPage schema only for FAQs visibly rendered on the page.",
        "Product/Offer schema only when pricing/offers are real and visible.",
        "Organization schema for entity clarity if not already present site-wide.",
    ]
    pr_steps = [
        f"Update the page mapped to {page_url}.",
        "Add the recommended answer/proof/comparison/FAQ sections where they fit naturally.",
        "Choose one metadata variant or rewrite it with the same intent.",
        "Add matching schema only for visible content.",
        "Run the site build, deploy, then recrawl and monitor GSC/GA4 movement.",
    ]

    return {
        "title": brief_title,
        "page_url": page_url,
        "target_keyword": keyword,
        "current_state": {
            "title": current_title,
            "meta_description": current_meta,
            "word_count": word_count,
            "schema_types": page.schema_types if page else [],
        },
        "impact": {
            "gsc_clicks": clicks,
            "gsc_impressions": impressions,
            "gsc_ctr": ctr,
            "gsc_position": position,
            "ga_sessions": sessions,
            "ga_key_events": key_events,
            "ga_revenue": revenue,
        },
        "recommended_sections": recommended_sections,
        "metadata_variants": metadata_variants,
        "schema_suggestions": schema_suggestions,
        "github_pr_steps": pr_steps,
        "generation": {
            "mode": generation_mode,
            "ai_configured": is_ai_configured(),
            "ai_model": "claude-sonnet-4-5" if generation_mode == "ai_anthropic" else None,
            "ai_error": ai_error,
            "tone": ai_tone,
            "suggested_word_count": ai_suggested_word_count,
            "notes": ai_notes,
            "fallback_used": generation_mode != "ai_anthropic",
        },
        "risk_notes": [
            "Do not invent reviews, ratings, pricing, or customer proof.",
            "Do not add schema unless the same content is visible to users.",
            "Use PR review and recrawl proof before marking the opportunity fixed.",
        ],
    }


def serialize_content_brief(row: ContentBrief) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "site_id": str(row.site_id),
        "page_url": row.page_url,
        "target_keyword": row.target_keyword,
        "title": row.title,
        "status": row.status,
        "brief": row.brief or {},
        "github_pr_url": row.github_pr_url,
        "github_branch": row.github_branch,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
