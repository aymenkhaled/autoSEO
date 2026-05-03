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
from typing import Any, Literal, Optional
from pydantic import BaseModel

from config import get_settings
from dependencies import get_db, get_current_user
from schemas.auth import AuthContext
from schemas.issue import IssueResponse, IssueListResponse
from models.tables import ChangeLog, Issue, Page, Site
from packages.ai_engine.engine import AIProviderUnavailable
from packages.ai_engine.repo_patch import generate_repo_patch_preview
from packages.shared.fix_workflows import build_root_cause_workflow
from packages.shared.notifications import notify_org_users
from packages.shared.readiness import connection_status_payload
from packages.shared.seo_domain import (
    FIX_STATUS_DEPLOYED,
    FIX_STATUS_DEPLOYED_AFTER_MERGE,
    FIX_STATUS_GITHUB_PR_CREATED,
    issue_is_auto_fixable,
    normalize_fix_status,
)
from services.opportunities import issue_priorities
from services.github_connection import github_adapter_for_site
from services.proof_loop import create_proof_snapshot

router = APIRouter(tags=["issues"])
settings = get_settings()


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
    "missing_title": {
        "title": "Page has no title tag",
        "summary": "One or more pages are missing a <title> element entirely.",
        "why_it_matters": "The title tag is the strongest on-page signal for what a page is about. Without it, search engines may generate or omit the title in results.",
        "recommended_fix": "Add a unique, descriptive <title> to every page. Use route metadata, CMS fields, or a server-rendered head tag.",
        "severity_explanation": "High because a missing title directly hurts CTR and relevance scoring.",
    },
    "title_too_short": {
        "title": "Page title is too short",
        "summary": "One or more page titles are under 30 characters and may not be descriptive enough for search engines.",
        "why_it_matters": "Short titles waste valuable keyword real estate and can signal thin or placeholder content.",
        "recommended_fix": "Expand titles to 50–60 characters that describe the page topic and include the primary keyword.",
        "severity_explanation": "Medium because the page is indexed, but click-through rate and relevance may suffer.",
    },
    "title_too_long": {
        "title": "Page title is too long",
        "summary": "One or more page titles exceed 60 characters and will be truncated in search results.",
        "why_it_matters": "Truncated titles hide the message and reduce click-through rate.",
        "recommended_fix": "Shorten titles to 50–60 characters, keeping the primary keyword near the front.",
        "severity_explanation": "Low to medium; the page ranks but truncation hurts CTR.",
    },
    "missing_meta_description": {
        "title": "Page has no meta description",
        "summary": "One or more pages are missing a meta description tag.",
        "why_it_matters": "Search engines often use the meta description as the snippet in results. Without it, Google generates a snippet which may not be appealing.",
        "recommended_fix": "Write a unique 120–155 character meta description for each page that accurately previews the content and includes a natural call to action.",
        "severity_explanation": "High because it directly impacts click-through rate from search results.",
    },
    "meta_description_too_long": {
        "title": "Meta description is too long",
        "summary": "One or more meta descriptions exceed 155 characters and will be truncated.",
        "why_it_matters": "Truncated descriptions cut off the message users see in search snippets.",
        "recommended_fix": "Rewrite meta descriptions to 120–155 characters, placing the key message and CTA early.",
        "severity_explanation": "Low to medium; rankings are not directly affected but CTR may drop.",
    },
    "missing_h1": {
        "title": "Page has no H1 heading",
        "summary": "One or more pages are missing an <h1> element.",
        "why_it_matters": "The H1 is the primary on-page topic signal. Its absence can weaken relevance scoring and confuse the crawler about the page's main subject.",
        "recommended_fix": "Add one clear, keyword-relevant <h1> near the top of each page.",
        "severity_explanation": "High because H1 is a strong topical relevance signal.",
    },
    "multiple_h1": {
        "title": "Page has multiple H1 headings",
        "summary": "One or more pages contain more than one <h1> element.",
        "why_it_matters": "Multiple H1s dilute the topical focus and can confuse both users and crawlers about the primary subject.",
        "recommended_fix": "Use exactly one <h1> per page; demote additional top-level headings to <h2> or lower.",
        "severity_explanation": "Medium because the page is indexed but topical focus is weakened.",
    },
    "images_missing_alt_text": {
        "title": "Images are missing alt text",
        "summary": "One or more pages contain images without alt attributes.",
        "why_it_matters": "Alt text is the only way search engines understand image content, and it provides accessibility for screen readers.",
        "recommended_fix": "Add descriptive alt attributes to all meaningful images; use alt=\"\" for decorative images.",
        "severity_explanation": "Medium because it affects image search visibility and accessibility compliance.",
    },
    "missing_schema": {
        "title": "Page has no structured data",
        "summary": "One or more pages are missing JSON-LD or microdata structured data markup.",
        "why_it_matters": "Structured data enables rich results (FAQs, ratings, breadcrumbs) and helps search engines better understand page content.",
        "recommended_fix": "Add relevant JSON-LD schema (Organization, WebPage, Article, Product, etc.) based on the page type.",
        "severity_explanation": "Low to medium; indexing works without schema but rich-result opportunities are missed.",
    },
    "missing_canonical": {
        "title": "Page has no canonical URL",
        "summary": "One or more pages are missing a <link rel='canonical'> tag.",
        "why_it_matters": "Without a canonical, search engines must guess which URL is preferred, which can split ranking signals across duplicates.",
        "recommended_fix": "Add a self-referencing canonical tag to every page, pointing to the preferred URL.",
        "severity_explanation": "Medium because duplicate or parameter URLs can dilute link equity over time.",
    },
    "missing_charset": {
        "title": "Page is missing a charset declaration",
        "summary": "One or more pages lack a <meta charset> or Content-Type charset header.",
        "why_it_matters": "Without a charset declaration, browsers and crawlers may misinterpret special characters and render garbled text.",
        "recommended_fix": "Add <meta charset=\"utf-8\"> as the first element inside <head> on every page.",
        "severity_explanation": "Low in most modern browsers, but it can cause rendering or indexing anomalies for non-ASCII content.",
    },
    "thin_content": {
        "title": "Page has thin or low-quality content",
        "summary": "One or more pages have a very low word count and may be seen as thin or low-value by search engines.",
        "why_it_matters": "Google's quality algorithms penalise pages with little original, helpful content, especially after Helpful Content updates.",
        "recommended_fix": "Expand content to cover the topic comprehensively, add FAQs, examples, or supporting context to reach a meaningful depth.",
        "severity_explanation": "Medium to high depending on how central the page is to the site's ranking strategy.",
    },
}


DEFAULT_GUIDANCE = {
    "title": "SEO issue",
    "summary": "AutoSEO found a repeated SEO signal that needs review.",
    "why_it_matters": "Repeated or invalid signals can reduce crawl quality, ranking clarity, or search-result quality.",
    "recommended_fix": "Review the affected URLs and update the underlying template, CMS field, or route metadata.",
    "severity_explanation": "Severity is based on estimated SEO impact and affected page count.",
}


class RootCauseFixRequest(BaseModel):
    site_id: UUID
    issue_type: str
    mode: Literal["plan", "ai_preview", "github_pr"] = "plan"
    business_context: dict[str, Any] | None = None


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
        status_values = [FIX_STATUS_DEPLOYED, "applied", FIX_STATUS_DEPLOYED_AFTER_MERGE] if normalized == FIX_STATUS_DEPLOYED else [normalized]
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
        status_values = [FIX_STATUS_DEPLOYED, "applied", FIX_STATUS_DEPLOYED_AFTER_MERGE] if normalized == FIX_STATUS_DEPLOYED else [normalized]
        conditions.append(Issue.fix_status.in_(status_values))

    site_for_workflow = None
    connection_for_workflow = None
    if site_id:
        site_for_workflow = (
            await db.execute(select(Site).where(Site.id == site_id, Site.org_id == auth.org_id))
        ).scalar_one_or_none()
        if site_for_workflow:
            connection_for_workflow = connection_status_payload(site_for_workflow)

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
        workflow_examples = [
            {"issue_id": str(issue_id), "url": url, "current_value": current_value}
            for issue_id, current_value, url in examples
        ]

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
            "fix_workflow": build_root_cause_workflow(
                issue_type=row.type,
                count=int(row.count or 0),
                connection=connection_for_workflow,
                ownership_verified=bool(getattr(site_for_workflow, "ownership_verified", False)),
                examples=workflow_examples,
                ai_configured=bool(settings.ANTHROPIC_API_KEY),
            ),
            "examples": workflow_examples,
        })

    return {
        "groups": out,
        "total_groups": len(out),
        "note": "Use issue categories and root-cause groups over raw totals; crawl limits, free-tier sampling, and pagination can change the number of rows without changing the underlying problems.",
    }


@router.post("/root-cause-fix")
async def root_cause_fix_workflow(
    data: RootCauseFixRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return or execute the next action for a grouped/root-cause issue."""
    issue_type = data.issue_type.strip()
    site = (
        await db.execute(select(Site).where(Site.id == data.site_id, Site.org_id == auth.org_id))
    ).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    rows = (
        await db.execute(
            select(Issue, Page.url)
            .join(Page, Issue.page_id == Page.id, isouter=True)
            .where(
                Issue.site_id == data.site_id,
                Issue.org_id == auth.org_id,
                Issue.type == issue_type,
                Issue.fix_status == "pending",
            )
            .order_by(Issue.impact_score.desc(), Issue.created_at.desc())
            .limit(50)
        )
    ).all()
    examples = [
        {
            "issue_id": str(issue.id),
            "url": url,
            "current_value": issue.current_value,
        }
        for issue, url in rows
    ]
    guidance = _guidance(issue_type)
    connection = connection_status_payload(site)
    workflow = build_root_cause_workflow(
        issue_type=issue_type,
        count=len(rows),
        connection=connection,
        ownership_verified=bool(site.ownership_verified),
        examples=examples[:8],
        ai_configured=bool(settings.ANTHROPIC_API_KEY),
    )

    if data.mode == "plan":
        return {"mode": "plan", "site_id": str(site.id), "issue_type": issue_type, **guidance, "fix_workflow": workflow}

    async def _ai_preview(adapter, creds: dict) -> dict:
        analysis = await adapter.analyze_static_app(creds.get("project_root") or "")
        candidates = await adapter.candidate_files_for_issue(
            issue_type,
            project_root=creds.get("project_root") or "",
        )
        contexts = await adapter.read_text_files([item["path"] for item in candidates])
        preview = await generate_repo_patch_preview(
            issue_type=issue_type,
            title=guidance["title"],
            summary=guidance["summary"],
            recommended_fix=guidance["recommended_fix"],
            site_domain=site.domain,
            affected_urls=[example["url"] for example in examples if example.get("url")],
            examples=examples,
            manual_steps=workflow["manual_steps"],
            repo_analysis=analysis,
            file_contexts=contexts,
            project_root=creds.get("project_root") or "",
            business_context=data.business_context,
        )
        return {
            "mode": "ai_preview",
            "site_id": str(site.id),
            "issue_type": issue_type,
            **guidance,
            "fix_workflow": workflow,
            "repo_analysis": analysis,
            "ai_preview": preview,
        }

    if data.mode == "ai_preview":
        if not workflow["can_preview_ai"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "AI preview is not ready for this root cause yet.",
                    "missing_requirements": workflow["missing_requirements"],
                },
            )
        adapter, creds = await github_adapter_for_site(str(auth.org_id), site)
        try:
            return await _ai_preview(adapter, creds)
        except AIProviderUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    if not workflow["can_create_github_pr"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "GitHub PR fixing is not ready for this root cause yet.",
                "missing_requirements": workflow["missing_requirements"],
            },
        )

    adapter, creds = await github_adapter_for_site(str(auth.org_id), site)
    if workflow["github_strategy"] == "safe_file_patch":
        result = await adapter.create_static_fix_pr(
            issue_type=issue_type,
            title=guidance["title"],
            site_domain=site.domain,
            affected_urls=[example["url"] for example in examples if example.get("url")],
            manual_steps=workflow["manual_steps"],
            project_root=creds.get("project_root") or "",
            build_command=creds.get("build_command"),
            package_manager=creds.get("package_manager"),
        )
        preview = None
    else:
        try:
            preview_payload = await _ai_preview(adapter, creds)
        except AIProviderUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        preview = preview_payload["ai_preview"]
        if not preview.get("safety", {}).get("ok", False):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "AI patch failed safety validation. Review the preview and required data.",
                    "safety": preview.get("safety"),
                    "ai_preview": preview,
                },
            )
        result = await adapter.create_ai_patch_pr(
            issue_type=issue_type,
            title=guidance["title"],
            site_domain=site.domain,
            affected_urls=[example["url"] for example in examples if example.get("url")],
            preview=preview,
            project_root=creds.get("project_root") or "",
        )
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result)

    proof_snapshot = await create_proof_snapshot(
        db,
        site=site,
        snapshot_type="before_pr",
        issue_type=issue_type,
        created_by=auth.user_id,
        evidence={
            "trigger": "github_fix_pr_created",
            "pr_url": result.get("pr_url"),
            "pr_number": result.get("pr_number"),
            "branch": result.get("branch"),
            "mode": result.get("mode"),
            "files_changed": result.get("files_changed", []),
            "ai_model": result.get("ai_model") or (preview or {}).get("ai_model"),
            "risk_level": result.get("risk_level") or (preview or {}).get("risk_level"),
        },
    )

    matching_issues = [issue for issue, _url in rows]
    for issue in matching_issues:
        issue.fix_status = FIX_STATUS_GITHUB_PR_CREATED
        issue.proposed_fix_metadata = {
            **(issue.proposed_fix_metadata or {}),
            "workflow": "github_static_root_cause",
            "issue_type": issue_type,
            "pr_url": result.get("pr_url"),
            "pr_number": result.get("pr_number"),
            "branch": result.get("branch"),
            "mode": result.get("mode"),
            "files_changed": result.get("files_changed", []),
            "ai_model": result.get("ai_model") or (preview or {}).get("ai_model"),
            "risk_level": result.get("risk_level") or (preview or {}).get("risk_level"),
            "recrawl_verification_status": "pending_deploy_recrawl",
            "proof_snapshot_id": str(proof_snapshot.id),
        }

    db.add(
        ChangeLog(
            org_id=auth.org_id,
            site_id=site.id,
            action="github_fix_pr_created",
            actor_type="user",
            actor_id=auth.user_id,
            new_value=result.get("pr_url"),
            extra_metadata={
                "issue_type": issue_type,
                "affected_count": len(matching_issues),
                "mode": result.get("mode"),
                "files_changed": result.get("files_changed", []),
                "ai_model": result.get("ai_model") or (preview or {}).get("ai_model"),
                "risk_level": result.get("risk_level") or (preview or {}).get("risk_level"),
                "recrawl_verification_status": "pending_deploy_recrawl",
                "proof_snapshot_id": str(proof_snapshot.id),
            },
        )
    )
    await notify_org_users(
        db,
        site.org_id,
        notification_type="fix.pr_created",
        title=f"GitHub PR created for {site.name}",
        body=f"{guidance['title']} is now tracked in a GitHub PR.",
        data={
            "site_id": str(site.id),
            "issue_type": issue_type,
            "pr_url": result.get("pr_url"),
            "pr_number": result.get("pr_number"),
        },
    )
    await db.commit()

    try:
        from routers.webhooks import emit_outbound_webhooks

        await emit_outbound_webhooks(
            db,
            site.org_id,
            "fix.pr_created",
            {
                "site_id": str(site.id),
                "site_name": site.name,
                "issue_type": issue_type,
                "affected_count": len(matching_issues),
                "pr_url": result.get("pr_url"),
                "pr_number": result.get("pr_number"),
                        "mode": result.get("mode"),
                        "risk_level": result.get("risk_level") or (preview or {}).get("risk_level"),
                    },
                )
    except Exception:
        pass

    return {
        "mode": "github_pr",
        "site_id": str(site.id),
        "issue_type": issue_type,
        "fix_workflow": {**workflow, "status": FIX_STATUS_GITHUB_PR_CREATED},
        "github": result,
        "ai_preview": preview,
        "proof_snapshot_id": str(proof_snapshot.id),
    }


@router.get("/prioritized")
async def prioritized_issues(
    site_id: UUID = Query(...),
    fix_status: Optional[str] = Query("pending"),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = (
        await db.execute(select(Site).where(Site.id == site_id, Site.org_id == auth.org_id))
    ).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    priorities = await issue_priorities(db, site=site, fix_status=fix_status or "pending")
    return {
        "site_id": str(site.id),
        "issues": priorities,
        "total": len(priorities),
        "message": "Priority combines technical severity, affected pages, GSC visibility, estimated click loss, and fix readiness.",
    }


@router.post("/bulk-dismiss")
async def bulk_dismiss_issues(
    data: dict,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dismiss multiple issues at once.

    Body: { "issue_ids": ["uuid1", "uuid2", ...], "reason": "optional reason" }
    Marks all matching (org-owned) issues as fix_status=dismissed.
    """
    from sqlalchemy import update as sa_update

    raw_ids = data.get("issue_ids") or []
    if not raw_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="issue_ids must be a non-empty list")
    if len(raw_ids) > 500:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot dismiss more than 500 issues at once")

    try:
        issue_ids = [UUID(str(i)) for i in raw_ids]
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="All issue_ids must be valid UUIDs")

    reason = str(data.get("reason") or "dismissed_by_user")[:255]

    result = await db.execute(
        sa_update(Issue)
        .where(Issue.id.in_(issue_ids), Issue.org_id == auth.org_id)
        .values(fix_status="dismissed")
        .returning(Issue.id, Issue.site_id)
    )
    dismissed_rows = result.all()
    await db.commit()

    dismissed_ids = [str(row[0]) for row in dismissed_rows]
    site_ids = list({str(row[1]) for row in dismissed_rows})

    for site_id in site_ids:
        db.add(ChangeLog(
            org_id=auth.org_id,
            site_id=UUID(site_id),
            action="bulk_dismiss",
            actor_type="user",
            actor_id=auth.user_id,
            new_value="dismissed",
            extra_metadata={"count": len(dismissed_ids), "reason": reason, "issue_ids": dismissed_ids[:50]},
        ))
    if site_ids:
        await db.commit()

    return {
        "dismissed_count": len(dismissed_ids),
        "dismissed_ids": dismissed_ids,
        "not_found_count": len(issue_ids) - len(dismissed_ids),
        "reason": reason,
        "message": f"Dismissed {len(dismissed_ids)} issue(s). They will be excluded from open-issue counts and fix queues.",
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
