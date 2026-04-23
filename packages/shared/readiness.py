"""Shared product readiness and site setup helpers."""
from __future__ import annotations

from typing import Any

from packages.shared.seo_domain import (
    AUTO_DEPLOY_CONNECTION_TYPES,
    connection_capabilities,
)

READINESS_WORKING = "working"
READINESS_SETUP_REQUIRED = "setup_required"
READINESS_MONITORING_ONLY = "monitoring_only"
READINESS_TRACKING_ONLY = "tracking_only"
READINESS_SAVED_ONLY = "saved_only"
READINESS_UNAVAILABLE_WITHOUT_PROVIDER = "unavailable_without_provider"

READINESS_LABELS = {
    READINESS_WORKING: "Working",
    READINESS_SETUP_REQUIRED: "Setup required",
    READINESS_MONITORING_ONLY: "Monitoring only",
    READINESS_TRACKING_ONLY: "Tracking only",
    READINESS_SAVED_ONLY: "Saved only",
    READINESS_UNAVAILABLE_WITHOUT_PROVIDER: "Needs external provider",
}

READINESS_DESCRIPTIONS = {
    READINESS_WORKING: "This feature is fully active in the current environment.",
    READINESS_SETUP_REQUIRED: "A setup step is still required before this flow is complete.",
    READINESS_MONITORING_ONLY: "This flow can audit or observe the site, but it cannot deploy changes.",
    READINESS_TRACKING_ONLY: "Records can be stored and organized, but live data has not been connected yet.",
    READINESS_SAVED_ONLY: "Configuration is stored, but automated delivery has not been wired yet.",
    READINESS_UNAVAILABLE_WITHOUT_PROVIDER: "This needs an external provider before the missing data can appear.",
}

MONITORING_MODE_LABELS = {
    "crawler": "Crawler",
    "snippet": "Snippet",
}

WRITE_INTEGRATION_LABELS = {
    "wordpress": "WordPress",
    "shopify": "Shopify",
    "webflow": "Webflow",
    "github": "GitHub",
}


def readiness_payload(state: str, *, label: str | None = None, description: str | None = None) -> dict[str, str]:
    normalized = state if state in READINESS_LABELS else READINESS_SETUP_REQUIRED
    return {
        "state": normalized,
        "label": label or READINESS_LABELS[normalized],
        "description": description or READINESS_DESCRIPTIONS[normalized],
    }


def split_connection_type(connection_type: str | None) -> dict[str, Any]:
    value = str(connection_type or "crawler")
    if value == "snippet":
        return {
            "connection_type": value,
            "monitoring_mode": "snippet",
            "monitoring_mode_label": MONITORING_MODE_LABELS["snippet"],
            "write_integration": None,
            "write_integration_label": "Not configured",
        }
    if value in AUTO_DEPLOY_CONNECTION_TYPES:
        return {
            "connection_type": value,
            "monitoring_mode": "crawler",
            "monitoring_mode_label": MONITORING_MODE_LABELS["crawler"],
            "write_integration": value,
            "write_integration_label": WRITE_INTEGRATION_LABELS.get(value, value.title()),
        }
    return {
        "connection_type": value,
        "monitoring_mode": "crawler",
        "monitoring_mode_label": MONITORING_MODE_LABELS["crawler"],
        "write_integration": None,
        "write_integration_label": "Not configured",
    }


def connection_status_payload(site) -> dict[str, Any]:
    split = split_connection_type(getattr(site, "connection_type", "crawler"))
    write_integration = split["write_integration"]
    write_configured = bool(write_integration and getattr(site, "cms_token_encrypted", None))
    capabilities = connection_capabilities(write_integration or split["monitoring_mode"])
    readiness = (
        readiness_payload(READINESS_WORKING, label="Write integration ready")
        if write_configured
        else readiness_payload(
            READINESS_MONITORING_ONLY,
            label="Monitoring only",
            description=(
                "AutoSEO can audit this site, but writable CMS deployment is not configured."
                if split["monitoring_mode"] == "crawler"
                else "The snippet can collect runtime data after installation, but deployment stays read-only."
            ),
        )
    )
    return {
        **split,
        "configured": bool(write_configured or split["monitoring_mode"] == "snippet"),
        "write_integration_configured": write_configured,
        "auto_deploy_capable": bool(write_configured and write_integration in AUTO_DEPLOY_CONNECTION_TYPES),
        "supported_fix_fields": capabilities.get("supported_fix_fields", []),
        "readiness": readiness["state"],
        "readiness_label": readiness["label"],
        "explanation": readiness["description"],
    }


def site_setup_payload(site, latest_crawl) -> dict[str, Any]:
    connection = connection_status_payload(site)
    has_completed_crawl = bool(latest_crawl)

    if not getattr(site, "ownership_verified", False):
        overall = readiness_payload(
            READINESS_SETUP_REQUIRED,
            label="Verification required",
            description="You can crawl the site now, but ownership verification is still required before trust-sensitive actions.",
        )
    elif not has_completed_crawl:
        overall = readiness_payload(
            READINESS_SETUP_REQUIRED,
            label="First crawl pending",
            description="Start a crawl to populate the site workspace with real pages, issues, and reports.",
        )
    elif connection["write_integration_configured"]:
        overall = readiness_payload(
            READINESS_WORKING,
            label="Monitoring and deployment ready",
            description="The site is verified, crawled, and connected to a writable integration.",
        )
    else:
        overall = readiness_payload(
            READINESS_MONITORING_ONLY,
            label="Monitoring only",
            description="The site is being monitored correctly, but deploy-capable integration is not configured.",
        )

    return {
        **overall,
        "ownership_verified": bool(getattr(site, "ownership_verified", False)),
        "monitoring_mode": connection["monitoring_mode"],
        "monitoring_mode_label": connection["monitoring_mode_label"],
        "write_integration": connection["write_integration"],
        "write_integration_label": connection["write_integration_label"],
        "write_integration_configured": connection["write_integration_configured"],
        "auto_deploy_capable": connection["auto_deploy_capable"],
        "steps": [
            {
                "key": "verification",
                "label": "Ownership verification",
                "done": bool(getattr(site, "ownership_verified", False)),
                "description": (
                    "Verified. High-trust actions can proceed."
                    if getattr(site, "ownership_verified", False)
                    else "Verify ownership before treating this property as fully trusted."
                ),
            },
            {
                "key": "monitoring",
                "label": "Monitoring mode",
                "done": True,
                "description": f"{connection['monitoring_mode_label']} is the current monitoring mode.",
            },
            {
                "key": "write_integration",
                "label": "Write integration",
                "done": bool(connection["write_integration_configured"]),
                "description": (
                    f"{connection['write_integration_label']} can deploy supported fields."
                    if connection["write_integration_configured"]
                    else "No writable integration is configured yet; fixes remain manual or monitoring-only."
                ),
            },
            {
                "key": "first_crawl",
                "label": "First crawl",
                "done": has_completed_crawl,
                "description": (
                    "Crawl data is available."
                    if has_completed_crawl
                    else "Run the first crawl to populate pages, grouped issues, and reports."
                ),
            },
        ],
    }
