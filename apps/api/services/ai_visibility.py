"""AI answer-readiness scoring based on crawl, schema, and content signals."""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.tables import AiVisibilityPrompt, AiVisibilityRun, Issue, Page, Site


def _tokens(text: str) -> set[str]:
    return {item for item in re.findall(r"[a-z0-9]{3,}", text.lower()) if item not in {"https", "www", "com"}}


async def build_ai_visibility_run(
    db: AsyncSession,
    *,
    site: Site,
    prompt: str,
    target_entity: str | None,
    competitor_domains: list[str] | None,
    created_by,
) -> AiVisibilityRun:
    pages = (
        await db.execute(
            select(Page)
            .where(Page.site_id == site.id, Page.org_id == site.org_id)
            .order_by(Page.seo_score.desc().nullslast(), Page.created_at.desc())
            .limit(25)
        )
    ).scalars().all()
    issue_counts = {
        row_type: int(count)
        for row_type, count in (
            await db.execute(
                select(Issue.type, func.count(Issue.id))
                .where(Issue.site_id == site.id, Issue.org_id == site.org_id, Issue.fix_status == "pending")
                .group_by(Issue.type)
            )
        ).all()
    }

    prompt_tokens = _tokens(prompt)
    entity_tokens = _tokens(target_entity or site.name or site.domain)
    title_text = " ".join(page.title or "" for page in pages)
    meta_text = " ".join(page.meta_description or "" for page in pages)
    heading_text = " ".join(" ".join(page.h1_text or []) for page in pages)
    content_tokens = _tokens(f"{title_text} {meta_text} {heading_text}")

    entity_overlap = len(entity_tokens & content_tokens) / max(1, len(entity_tokens))
    prompt_overlap = len(prompt_tokens & content_tokens) / max(1, len(prompt_tokens))
    schema_rich_pages = sum(1 for page in pages if page.schema_types)
    faq_or_howto = sum(1 for page in pages if set(page.schema_types or []) & {"FAQPage", "HowTo", "Article", "Product"})
    citation_signals = min(1.0, (schema_rich_pages / max(1, len(pages))) + (faq_or_howto / max(2, len(pages))))

    blockers = []
    if issue_counts.get("spa_no_prerender"):
        blockers.append("Important public pages may look empty to crawlers and AI retrieval systems.")
    if issue_counts.get("duplicate_title"):
        blockers.append("Repeated titles make entity/page purpose less clear.")
    if issue_counts.get("unverified_review_schema"):
        blockers.append("Review/rating markup needs proof before it can be trusted.")
    if issue_counts.get("missing_sitemap") or issue_counts.get("missing_robots"):
        blockers.append("Discovery files are incomplete, which can weaken crawl and retrieval coverage.")

    missing_context = []
    if prompt_overlap < 0.2:
        missing_context.append("The prompt topic is not strongly represented in crawled titles/headings.")
    if entity_overlap < 0.5:
        missing_context.append("The target entity is not repeated clearly across important page metadata.")
    if citation_signals < 0.35:
        missing_context.append("Pages need more citation-friendly structure such as FAQ, HowTo, Article, Product, or Organization schema.")
    missing_context.extend(blockers)

    recommendations = [
        "Create concise answer blocks for the target prompt on the best matching page.",
        "Strengthen entity wording in title, H1, meta description, and schema.",
        "Add FAQ or Article/Product structured data only when it matches visible page content.",
    ]
    if issue_counts.get("spa_no_prerender"):
        recommendations.insert(0, "Fix SPA/prerendering first so crawlers and AI systems can read the page without executing the full app.")
    if issue_counts.get("duplicate_title"):
        recommendations.append("Give each important route a unique title that names the page purpose and entity.")

    entity_score = int(round(entity_overlap * 100))
    citation_score = int(round(citation_signals * 100))
    visibility_score = max(1, min(100, int(round((prompt_overlap * 45) + (entity_overlap * 30) + (citation_signals * 25) - len(blockers) * 7))))
    competitor_mentions = [
        {
            "domain": domain,
            "status": "tracked_for_prompt",
            "note": "AutoSEO records competitor candidates here; live AI-answer checking requires a provider/browser research connector.",
        }
        for domain in (competitor_domains or [])[:8]
    ]

    prompt_row = AiVisibilityPrompt(
        org_id=site.org_id,
        site_id=site.id,
        prompt=prompt,
        target_entity=target_entity,
        competitor_domains=competitor_domains or [],
        created_by=created_by,
    )
    db.add(prompt_row)
    await db.flush()

    run = AiVisibilityRun(
        org_id=site.org_id,
        site_id=site.id,
        prompt_id=prompt_row.id,
        prompt=prompt,
        status="completed",
        visibility_score=visibility_score,
        entity_score=entity_score,
        citation_score=citation_score,
        competitor_mentions=competitor_mentions,
        missing_context=missing_context,
        recommendations=recommendations,
        evidence={
            "pages_scored": len(pages),
            "prompt_overlap": round(prompt_overlap, 4),
            "entity_overlap": round(entity_overlap, 4),
            "schema_rich_pages": schema_rich_pages,
            "faq_or_howto_pages": faq_or_howto,
            "pending_issue_counts": issue_counts,
            "provider_status": "readiness_scoring_only",
            "provider_note": "No external AI-answer engine was queried for this run.",
        },
        created_by=created_by,
    )
    db.add(run)
    await db.flush()
    return run


def serialize_ai_visibility_run(run: AiVisibilityRun) -> dict[str, Any]:
    return {
        "id": str(run.id),
        "prompt": run.prompt,
        "status": run.status,
        "visibility_score": run.visibility_score,
        "entity_score": run.entity_score,
        "citation_score": run.citation_score,
        "competitor_mentions": run.competitor_mentions or [],
        "missing_context": run.missing_context or [],
        "recommendations": run.recommendations or [],
        "evidence": run.evidence or {},
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }
