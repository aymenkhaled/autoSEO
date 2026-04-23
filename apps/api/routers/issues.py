"""Issues router — list, filter, and view SEO issues.

Phase 2 additions:
- Missing Feature 6: aggregated view groups identical issue types across pages
  so the UI can show "300 pages missing meta description" as one row instead
  of 300 separate rows.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from typing import Optional

from dependencies import get_db, get_current_user
from schemas.auth import AuthContext
from schemas.issue import IssueResponse, IssueListResponse
from models.tables import Issue, Page
from packages.shared.seo_domain import FIX_STATUS_DEPLOYED, issue_is_auto_fixable, normalize_fix_status

router = APIRouter(tags=["issues"])


ISSUE_GUIDANCE = {
    "spa_no_prerender": {
        "title": "Pages render as an empty SPA shell",
        "summary": "Search crawlers are receiving the JavaScript shell instead of page-specific HTML.",
        "why_it_matters": "If the initial HTML has no real content, titles, headings, or body copy per route, indexability can collapse even when the browser looks fine.",
        "recommended_fix": "Add SSR/prerendering for public routes, or generate static HTML per route before crawl/index time.",
        "severity_explanation": "Critical because crawlers can miss the actual page content.",
    },
    "duplicate_title": {
        "title": "Multiple pages share the same title",
        "summary": "Routes are reusing one static title instead of a unique title per page.",
        "why_it_matters": "Duplicate titles make pages compete with each other and reduce click relevance in search results.",
        "recommended_fix": "Generate a unique title per route from route metadata, CMS fields, or server-rendered head tags.",
        "severity_explanation": "High/medium depending on how many URLs share the same title.",
    },
    "keyword_cannibalization": {
        "title": "Pages target the same search intent",
        "summary": "Several URLs appear to target the same primary query.",
        "why_it_matters": "Search engines may rotate or split ranking signals across similar pages.",
        "recommended_fix": "Merge overlapping pages, canonicalize weaker pages, or rewrite each page for a distinct intent.",
        "severity_explanation": "Medium because it usually degrades performance rather than fully blocking indexing.",
    },
    "stale_schema_date": {
        "title": "Structured data contains an expired offer date",
        "summary": "JSON-LD includes priceValidUntil/validThrough values that are already in the past.",
        "why_it_matters": "Expired offer markup can make rich results invalid or misleading.",
        "recommended_fix": "Update or remove expired date fields in Product/Offer JSON-LD.",
        "severity_explanation": "Medium because it affects rich-result eligibility and trust.",
    },
    "unverified_review_schema": {
        "title": "Review/rating schema needs proof",
        "summary": "JSON-LD includes aggregateRating or named reviews that should match real visible review sources.",
        "why_it_matters": "Unsupported review markup can violate Google review-snippet policy and create manual-action risk.",
        "recommended_fix": "Remove fake/testimonial-only review markup, or connect it to real first-party reviews visible on the page.",
        "severity_explanation": "High because policy violations can affect rich results and trust.",
    },
    "missing_sitemap": {
        "title": "Missing sitemap.xml",
        "summary": "AutoSEO could not verify a public /sitemap.xml endpoint.",
        "why_it_matters": "Sitemaps help discovery, freshness, and large-site crawl coverage.",
        "recommended_fix": "Publish a valid XML sitemap and reference it from robots.txt.",
        "severity_explanation": "Medium because discovery may still work through links, but coverage is weaker.",
    },
    "missing_robots": {
        "title": "Missing robots.txt",
        "summary": "AutoSEO could not verify a public /robots.txt endpoint.",
        "why_it_matters": "robots.txt documents crawler rules and is the standard place to advertise sitemaps.",
        "recommended_fix": "Publish robots.txt with sensible allow rules and a Sitemap directive.",
        "severity_explanation": "Medium because absence is allowed, but it removes crawler guidance.",
    },
    "missing_offer_schema": {
        "title": "Visible offer missing from JSON-LD",
        "summary": "A visible lifetime/$499 offer appears on the page but is absent from structured data offers.",
        "why_it_matters": "Search engines and integrations may see incomplete pricing data.",
        "recommended_fix": "Add the missing offer to Product/Offer JSON-LD or remove stale/incomplete offer markup.",
        "severity_explanation": "Medium because it affects structured-data completeness.",
    },
    "broken_og_image": {
        "title": "Open Graph image is missing or unreachable",
        "summary": "The og:image URL could not be validated as a public reachable asset.",
        "why_it_matters": "Broken OG images make social shares look empty or untrusted.",
        "recommended_fix": "Use an absolute public HTTPS image URL and confirm it returns 200.",
        "severity_explanation": "Medium because it affects sharing, not core indexability.",
    },
}


DEFAULT_GUIDANCE = {
    "title": "SEO issue",
    "summary": "AutoSEO found a repeated SEO signal that needs review.",
    "why_it_matters": "Repeated or invalid signals can reduce crawl quality, ranking clarity, or search-result quality.",
    "recommended_fix": "Review the affected URLs and update the underlying template, CMS field, or route metadata.",
    "severity_explanation": "Severity is based on estimated SEO impact and affected page count.",
}


def _guidance(issue_type: str) -> dict:
    return {**DEFAULT_GUIDANCE, **ISSUE_GUIDANCE.get(issue_type, {})}


@router.get("", response_model=IssueListResponse)
async def list_issues(
    site_id: UUID = Query(None),
    crawl_id: UUID = Query(None),
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    fix_status: Optional[str] = Query(None),
    fix_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List issues with optional filters."""
    query = select(Issue).where(Issue.org_id == auth.org_id)
    count_query = select(func.count(Issue.id)).where(Issue.org_id == auth.org_id)

    # Apply filters
    if site_id:
        query = query.where(Issue.site_id == site_id)
        count_query = count_query.where(Issue.site_id == site_id)
    if crawl_id:
        query = query.where(Issue.crawl_id == crawl_id)
        count_query = count_query.where(Issue.crawl_id == crawl_id)
    if category:
        query = query.where(Issue.category == category)
        count_query = count_query.where(Issue.category == category)
    if severity:
        query = query.where(Issue.severity == severity)
        count_query = count_query.where(Issue.severity == severity)
    if fix_status:
        normalized = normalize_fix_status(fix_status)
        status_values = [FIX_STATUS_DEPLOYED, "applied"] if normalized == FIX_STATUS_DEPLOYED else [normalized]
        query = query.where(Issue.fix_status.in_(status_values))
        count_query = count_query.where(Issue.fix_status.in_(status_values))
    if fix_type:
        query = query.where(Issue.fix_type == fix_type)
        count_query = count_query.where(Issue.fix_type == fix_type)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * per_page
    result = await db.execute(
        query.order_by(Issue.impact_score.desc()).offset(offset).limit(per_page)
    )
    issues = result.scalars().all()

    return IssueListResponse(issues=issues, total=total)


@router.get("/aggregated")
async def list_aggregated_issues(
    site_id: UUID = Query(None),
    crawl_id: UUID = Query(None),
    severity: Optional[str] = Query(None),
    fix_status: Optional[str] = Query("pending"),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Group issues by type so the UI can present them as patterns instead of a flood
    (Missing Feature 6 from the gap analysis).

    Returns one row per issue type with: count, max severity, total impact,
    sample affected URLs, and whether the group can be bulk-fixed.
    """
    conditions = [Issue.org_id == auth.org_id]
    if site_id:
        conditions.append(Issue.site_id == site_id)
    if crawl_id:
        conditions.append(Issue.crawl_id == crawl_id)
    if severity:
        conditions.append(Issue.severity == severity)
    if fix_status:
        normalized = normalize_fix_status(fix_status)
        status_values = [FIX_STATUS_DEPLOYED, "applied"] if normalized == FIX_STATUS_DEPLOYED else [normalized]
        conditions.append(Issue.fix_status.in_(status_values))

    # Aggregate at the DB level to keep this cheap on large sites
    agg = (await db.execute(
        select(
            Issue.type,
            Issue.category,
            func.max(Issue.severity).label("severity"),
            func.count(Issue.id).label("count"),
            func.sum(Issue.impact_score).label("total_impact"),
            func.max(Issue.fix_type).label("fix_type"),
        )
        .where(*conditions)
        .group_by(Issue.type, Issue.category)
        .order_by(func.sum(Issue.impact_score).desc())
    )).all()

    # For each group, fetch examples (joined to pages when available). Site-wide
    # issues such as missing_sitemap intentionally have no page_id.
    out = []
    for row in agg:
        examples = (await db.execute(
            select(Issue.id, Issue.current_value, Page.url)
            .join(Page, Issue.page_id == Page.id, isouter=True)
            .where(*conditions, Issue.type == row.type, Issue.category == row.category)
            .order_by(Issue.impact_score.desc(), Issue.created_at.desc())
            .limit(8)
        )).all()
        guidance = _guidance(row.type)
        sample_urls = [url for _, _, url in examples if url]

        out.append({
            "type": row.type,
            **guidance,
            "category": row.category,
            "severity": row.severity,
            "count": int(row.count or 0),
            "total_impact": int(row.total_impact or 0),
            "fix_type": row.fix_type,
            "can_bulk_fix": issue_is_auto_fixable(row.type),
            "sample_urls": list(sample_urls),
            "examples": [
                {
                    "issue_id": str(issue_id),
                    "url": url,
                    "current_value": current_value,
                }
                for issue_id, current_value, url in examples
            ],
        })

    return {
        "groups": out,
        "total_groups": len(out),
        "note": "Use issue categories and root-cause groups over raw totals; crawl limits, free-tier sampling, and pagination can change the number of rows without changing the underlying problems.",
    }


@router.get("/{issue_id}", response_model=IssueResponse)
async def get_issue(
    issue_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific issue with full details."""
    result = await db.execute(
        select(Issue).where(Issue.id == issue_id, Issue.org_id == auth.org_id)
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    return issue
