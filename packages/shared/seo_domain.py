"""Shared SEO domain constants and helpers.

This module centralizes issue names, fix-field mappings, deployment
capabilities, and lifecycle states so the API, workers, crawler, and frontend
can speak the same language.
"""
from __future__ import annotations

from typing import Final


FIX_STATUS_PENDING: Final[str] = "pending"
FIX_STATUS_APPROVED: Final[str] = "approved"
FIX_STATUS_DEPLOYED: Final[str] = "deployed"
FIX_STATUS_APPLY_FAILED: Final[str] = "apply_failed"
FIX_STATUS_ROLLED_BACK: Final[str] = "rolled_back"
FIX_STATUS_REJECTED_UNSAFE: Final[str] = "rejected_unsafe"
FIX_STATUS_DIAGNOSED: Final[str] = "diagnosed"
FIX_STATUS_MANUAL_INSTRUCTIONS_READY: Final[str] = "manual_instructions_ready"
FIX_STATUS_GITHUB_PR_READY: Final[str] = "github_pr_ready"
FIX_STATUS_GITHUB_PR_CREATED: Final[str] = "github_pr_created"
FIX_STATUS_DEPLOYED_AFTER_MERGE: Final[str] = "deployed_after_merge"
FIX_STATUS_CANNOT_AUTO_FIX: Final[str] = "cannot_auto_fix"

LEGACY_FIX_STATUS_ALIASES: Final[dict[str, str]] = {
    "applied": FIX_STATUS_DEPLOYED,
}


ISSUE_MISSING_TITLE: Final[str] = "missing_title"
ISSUE_TITLE_TOO_SHORT: Final[str] = "title_too_short"
ISSUE_TITLE_TOO_LONG: Final[str] = "title_too_long"
ISSUE_DUPLICATE_TITLE: Final[str] = "duplicate_title"
ISSUE_MISSING_META_DESCRIPTION: Final[str] = "missing_meta_description"
ISSUE_META_DESCRIPTION_TOO_LONG: Final[str] = "meta_description_too_long"
ISSUE_DUPLICATE_META_DESCRIPTION: Final[str] = "duplicate_meta_description"
ISSUE_MISSING_H1: Final[str] = "missing_h1"
ISSUE_MISSING_SCHEMA: Final[str] = "missing_schema"
ISSUE_MISSING_CANONICAL: Final[str] = "missing_canonical"
ISSUE_IMAGES_MISSING_ALT_TEXT: Final[str] = "images_missing_alt_text"
ISSUE_SPA_NO_PRERENDER: Final[str] = "spa_no_prerender"
ISSUE_STALE_SCHEMA_DATE: Final[str] = "stale_schema_date"
ISSUE_UNVERIFIED_REVIEW_SCHEMA: Final[str] = "unverified_review_schema"
ISSUE_MISSING_SITEMAP: Final[str] = "missing_sitemap"
ISSUE_MISSING_ROBOTS: Final[str] = "missing_robots"
ISSUE_MISSING_OFFER_SCHEMA: Final[str] = "missing_offer_schema"
ISSUE_BROKEN_OG_IMAGE: Final[str] = "broken_og_image"

LEGACY_ISSUE_ALIASES: Final[dict[str, str]] = {
    "missing_alt_text": ISSUE_IMAGES_MISSING_ALT_TEXT,
    "broken_canonical": ISSUE_MISSING_CANONICAL,
}


FIX_FIELD_TITLE: Final[str] = "title"
FIX_FIELD_META_DESCRIPTION: Final[str] = "meta_description"
FIX_FIELD_OG_TITLE: Final[str] = "og_title"
FIX_FIELD_OG_DESCRIPTION: Final[str] = "og_description"
FIX_FIELD_CANONICAL: Final[str] = "canonical"
FIX_FIELD_H1: Final[str] = "h1"
FIX_FIELD_SCHEMA: Final[str] = "schema"
FIX_FIELD_ALT_TEXT: Final[str] = "alt_text"

ISSUE_TO_FIX_FIELD: Final[dict[str, str]] = {
    ISSUE_MISSING_TITLE: FIX_FIELD_TITLE,
    ISSUE_TITLE_TOO_SHORT: FIX_FIELD_TITLE,
    ISSUE_TITLE_TOO_LONG: FIX_FIELD_TITLE,
    ISSUE_DUPLICATE_TITLE: FIX_FIELD_TITLE,
    ISSUE_MISSING_META_DESCRIPTION: FIX_FIELD_META_DESCRIPTION,
    ISSUE_META_DESCRIPTION_TOO_LONG: FIX_FIELD_META_DESCRIPTION,
    ISSUE_DUPLICATE_META_DESCRIPTION: FIX_FIELD_META_DESCRIPTION,
    ISSUE_MISSING_CANONICAL: FIX_FIELD_CANONICAL,
    ISSUE_MISSING_H1: FIX_FIELD_H1,
    ISSUE_MISSING_SCHEMA: FIX_FIELD_SCHEMA,
    ISSUE_STALE_SCHEMA_DATE: FIX_FIELD_SCHEMA,
    ISSUE_MISSING_OFFER_SCHEMA: FIX_FIELD_SCHEMA,
    ISSUE_IMAGES_MISSING_ALT_TEXT: FIX_FIELD_ALT_TEXT,
}

AUTO_FIXABLE_ISSUES: Final[set[str]] = set(ISSUE_TO_FIX_FIELD.keys())


CONNECTION_FIELD_CAPABILITIES: Final[dict[str, set[str]]] = {
    "crawler": set(),
    "snippet": set(),
    "wordpress": {
        FIX_FIELD_TITLE,
        FIX_FIELD_META_DESCRIPTION,
        FIX_FIELD_OG_TITLE,
        FIX_FIELD_OG_DESCRIPTION,
    },
    "shopify": {
        FIX_FIELD_TITLE,
        FIX_FIELD_META_DESCRIPTION,
    },
    "webflow": {
        FIX_FIELD_TITLE,
        FIX_FIELD_META_DESCRIPTION,
        FIX_FIELD_OG_TITLE,
        FIX_FIELD_OG_DESCRIPTION,
    },
    "github": {
        FIX_FIELD_TITLE,
        FIX_FIELD_META_DESCRIPTION,
        FIX_FIELD_CANONICAL,
    },
}

AUTO_DEPLOY_CONNECTION_TYPES: Final[set[str]] = {
    "wordpress",
    "shopify",
    "webflow",
    "github",
}

CONNECTION_CAPABILITY_SUMMARY: Final[dict[str, dict[str, object]]] = {
    "crawler": {
        "label": "Crawler",
        "mode": "read_only",
        "description": "Audits public pages only. It can find issues and suggest manual fixes, but it cannot deploy changes.",
        "required_credentials": [],
    },
    "snippet": {
        "label": "JavaScript Snippet",
        "mode": "read_only_runtime",
        "description": "Collects runtime page data after installation. Direct deployment is intentionally disabled until snippet delivery is complete.",
        "required_credentials": ["snippet install code"],
    },
    "wordpress": {
        "label": "WordPress",
        "mode": "auto_deploy",
        "description": "Tests the WordPress REST API and can deploy supported title/meta description fixes when credentials and SEO plugin support allow it.",
        "required_credentials": ["site_url", "username", "app_password"],
    },
    "shopify": {
        "label": "Shopify",
        "mode": "auto_deploy",
        "description": "Tests the Shopify Admin API and can deploy supported product/page title and meta description fixes.",
        "required_credentials": ["shop_domain", "access_token"],
    },
    "webflow": {
        "label": "Webflow",
        "mode": "auto_deploy",
        "description": "Tests the Webflow Data API and can update supported SEO fields, then publish the page.",
        "required_credentials": ["site_id", "token"],
    },
    "github": {
        "label": "GitHub",
        "mode": "pr_or_repo_update",
        "description": "Uses repository access for file-based sites. Fixes should be reviewed through a PR-style workflow before going live.",
        "required_credentials": ["owner", "repo", "github_token", "branch"],
    },
}


def normalize_issue_type(issue_type: str | None) -> str:
    if not issue_type:
        return ""
    issue_type = str(issue_type).strip()
    return LEGACY_ISSUE_ALIASES.get(issue_type, issue_type)


def normalize_fix_status(status: str | None) -> str:
    if not status:
        return FIX_STATUS_PENDING
    status = str(status).strip()
    return LEGACY_FIX_STATUS_ALIASES.get(status, status)


def issue_to_fix_field(issue_type: str | None) -> str:
    issue_type = normalize_issue_type(issue_type)
    return ISSUE_TO_FIX_FIELD.get(issue_type, FIX_FIELD_TITLE)


def issue_is_auto_fixable(issue_type: str | None) -> bool:
    return normalize_issue_type(issue_type) in AUTO_FIXABLE_ISSUES


def supported_fix_fields(connection_type: str | None) -> set[str]:
    if not connection_type:
        return set()
    return set(CONNECTION_FIELD_CAPABILITIES.get(connection_type, set()))


def connection_capabilities(connection_type: str | None) -> dict[str, object]:
    key = str(connection_type or "crawler")
    summary = CONNECTION_CAPABILITY_SUMMARY.get(key, CONNECTION_CAPABILITY_SUMMARY["crawler"])
    supported = sorted(supported_fix_fields(key))
    return {
        **summary,
        "connection_type": key,
        "supported_fix_fields": supported,
        "unsupported_message": (
            "This connection is read-only for deployment."
            if not supported
            else "Only the listed fields can be auto-deployed; other issues remain manual."
        ),
    }


def connection_can_auto_deploy(connection_type: str | None) -> bool:
    return str(connection_type or "") in AUTO_DEPLOY_CONNECTION_TYPES


def issue_can_auto_deploy(issue_type: str | None, connection_type: str | None) -> bool:
    field = issue_to_fix_field(issue_type)
    return connection_can_auto_deploy(connection_type) and field in supported_fix_fields(connection_type)
