"""Deterministic root-cause fix recipes used by API and UI."""
from __future__ import annotations

from typing import Any

from packages.shared.seo_domain import (
    FIX_STATUS_CANNOT_AUTO_FIX,
    FIX_STATUS_GITHUB_PR_READY,
    FIX_STATUS_MANUAL_INSTRUCTIONS_READY,
)


GITHUB_STATIC_APP_ISSUES = {
    "spa_no_prerender",
    "duplicate_title",
    "stale_schema_date",
    "unverified_review_schema",
    "missing_sitemap",
    "missing_robots",
    "missing_offer_schema",
    "broken_og_image",
}


FIX_RECIPES: dict[str, dict[str, Any]] = {
    "spa_no_prerender": {
        "required_fix_type": "source_rendering_change",
        "github_strategy": "plan_only",
        "steps": [
            "Identify the public route definitions and metadata source for each affected URL.",
            "Add SSR, prerendering, or static HTML generation so crawlers receive route-specific HTML.",
            "Make title, meta description, canonical, schema, and visible body content available in the initial HTML.",
            "Build and deploy, then re-crawl the site to confirm the SPA-shell group disappears.",
        ],
    },
    "duplicate_title": {
        "required_fix_type": "route_metadata_change",
        "github_strategy": "plan_only",
        "steps": [
            "Create a route metadata registry or source route titles from the content model.",
            "Render a unique title for every indexable route before crawler/index time.",
            "Add a regression check so duplicate static titles cannot return.",
        ],
    },
    "stale_schema_date": {
        "required_fix_type": "schema_source_change",
        "github_strategy": "plan_only",
        "steps": [
            "Find Product/Offer JSON-LD in the source code or content data.",
            "Remove expired priceValidUntil/validThrough values or replace them with real current dates.",
            "Validate the JSON-LD after build and re-crawl.",
        ],
    },
    "unverified_review_schema": {
        "required_fix_type": "schema_policy_change",
        "github_strategy": "plan_only",
        "steps": [
            "Remove aggregateRating and named review JSON-LD unless the reviews are real and visible on the page.",
            "If real reviews exist, connect schema values to the real review source instead of hardcoded testimonials.",
            "Re-test rich-result eligibility after deployment.",
        ],
    },
    "missing_sitemap": {
        "required_fix_type": "public_asset_change",
        "github_strategy": "safe_file_patch",
        "steps": [
            "Add a public sitemap.xml with canonical URLs for the scanned site.",
            "Keep sitemap generation wired to future route/content changes.",
            "Reference the sitemap from robots.txt.",
        ],
    },
    "missing_robots": {
        "required_fix_type": "public_asset_change",
        "github_strategy": "safe_file_patch",
        "steps": [
            "Add public robots.txt with default allow rules.",
            "Include a Sitemap directive pointing to the production sitemap.",
            "Deploy and confirm /robots.txt returns 200.",
        ],
    },
    "missing_offer_schema": {
        "required_fix_type": "schema_business_data_change",
        "github_strategy": "plan_only",
        "steps": [
            "Confirm the real pricing/offers that should be represented.",
            "Update Product/Offer JSON-LD so visible pricing and structured data match.",
            "Remove offers that are no longer sold.",
        ],
    },
    "broken_og_image": {
        "required_fix_type": "public_asset_or_metadata_change",
        "github_strategy": "plan_only",
        "steps": [
            "Add a real public Open Graph image asset or update og:image to an existing HTTPS image.",
            "Use an absolute URL in production metadata.",
            "Verify the image returns 200 and is large enough for social previews.",
        ],
    },
}


DEFAULT_RECIPE = {
    "required_fix_type": "manual_review",
    "github_strategy": "manual_only",
    "steps": [
        "Review the affected URLs and current values.",
        "Update the source template, CMS field, or page content that produces the repeated issue.",
        "Deploy and re-crawl to verify the issue no longer appears.",
    ],
}


def build_root_cause_workflow(
    *,
    issue_type: str,
    count: int,
    connection: dict | None,
    ownership_verified: bool,
    examples: list[dict] | None = None,
) -> dict[str, Any]:
    recipe = {**DEFAULT_RECIPE, **FIX_RECIPES.get(issue_type, {})}
    write_integration = (connection or {}).get("write_integration")
    write_configured = bool((connection or {}).get("write_integration_configured"))
    github_possible = issue_type in GITHUB_STATIC_APP_ISSUES
    can_create_pr = bool(github_possible and write_integration == "github" and write_configured and ownership_verified)

    missing: list[str] = []
    if github_possible and write_integration != "github":
        missing.append("Connect GitHub as the fix deployment method.")
    if github_possible and write_integration == "github" and not write_configured:
        missing.append("Save and test real GitHub repository credentials.")
    if github_possible and not ownership_verified:
        missing.append("Verify site ownership before AutoSEO can create deployment PRs.")

    status = (
        FIX_STATUS_GITHUB_PR_READY
        if can_create_pr
        else FIX_STATUS_MANUAL_INSTRUCTIONS_READY
        if recipe["github_strategy"] != "manual_only"
        else FIX_STATUS_CANNOT_AUTO_FIX
    )

    return {
        "status": status,
        "required_fix_type": recipe["required_fix_type"],
        "github_strategy": recipe["github_strategy"],
        "can_create_github_pr": can_create_pr,
        "missing_requirements": missing,
        "affected_count": count,
        "examples": examples or [],
        "manual_steps": recipe["steps"],
        "action_label": "Create GitHub PR" if can_create_pr else "Show exact manual steps",
        "truth_note": (
            "Crawler and snippet modes can diagnose this root cause, but they cannot edit the site. "
            "GitHub PR fixing is available only after verification and a saved GitHub connection."
        ),
    }
