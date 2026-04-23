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


def connection_can_auto_deploy(connection_type: str | None) -> bool:
    return str(connection_type or "") in AUTO_DEPLOY_CONNECTION_TYPES


def issue_can_auto_deploy(issue_type: str | None, connection_type: str | None) -> bool:
    field = issue_to_fix_field(issue_type)
    return connection_can_auto_deploy(connection_type) and field in supported_fix_fields(connection_type)
