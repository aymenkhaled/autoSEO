"""System router — runtime readiness and environment-backed feature states."""
from __future__ import annotations

from fastapi import APIRouter

from config import get_settings
from packages.shared.readiness import (
    READINESS_SAVED_ONLY,
    READINESS_SETUP_REQUIRED,
    READINESS_UNAVAILABLE_WITHOUT_PROVIDER,
    READINESS_WORKING,
    readiness_payload,
)

router = APIRouter(tags=["system"])


@router.get("/readiness")
async def get_runtime_readiness():
    settings = get_settings()
    auth_mode = (
        "supabase"
        if settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY
        else "local_jwt"
    )
    ai_configured = bool(settings.ANTHROPIC_API_KEY)
    github_app_configured = bool(settings.GITHUB_APP_ID and settings.GITHUB_APP_PRIVATE_KEY and settings.GITHUB_APP_SLUG)
    stripe_configured = bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_WEBHOOK_SECRET)
    webhook_delivery_available = True

    return {
        "auth_mode": auth_mode,
        "providers": {
            "supabase": auth_mode == "supabase",
            "anthropic": ai_configured,
            "github_app": github_app_configured,
            "stripe": stripe_configured,
            "resend": bool(settings.RESEND_API_KEY),
            "webhooks": webhook_delivery_available,
        },
        "features": {
            "auth": readiness_payload(
                READINESS_WORKING,
                label="Supabase browser auth" if auth_mode == "supabase" else "Local email/password auth",
                description=(
                    "Browser auth uses Supabase session handling in this environment."
                    if auth_mode == "supabase"
                    else "Browser auth uses the local FastAPI JWT login/register flow in this environment."
                ),
            ),
            "ai_fixes": readiness_payload(
                READINESS_WORKING if ai_configured else READINESS_UNAVAILABLE_WITHOUT_PROVIDER,
                label="AI fix generation ready" if ai_configured else "Anthropic configuration required",
                description=(
                    "AI fix generation is configured and can create reviewable suggestions."
                    if ai_configured
                    else "Configure ANTHROPIC_API_KEY before AutoSEO can generate AI fixes or AI content suggestions."
                ),
            ),
            "billing": readiness_payload(
                READINESS_SETUP_REQUIRED if stripe_configured else READINESS_SAVED_ONLY,
                label="Stripe setup in progress" if stripe_configured else "Stripe wiring deferred",
                description=(
                    "Stripe credentials are present, but checkout/portal flows still need end-to-end wiring before upgrade actions should appear."
                    if stripe_configured
                    else "Billing state is stored and visible, but checkout and portal flows are intentionally disabled until Stripe is fully wired."
                ),
            ),
            "github_pr_fixes": readiness_payload(
                READINESS_WORKING if github_app_configured else READINESS_SETUP_REQUIRED,
                label="GitHub App ready" if github_app_configured else "GitHub App setup required",
                description=(
                    "GitHub App PR-only access is configured. Users can install the app on selected repositories."
                    if github_app_configured
                    else "Configure GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY, and GITHUB_APP_SLUG to enable the trusted SaaS GitHub App flow. Fine-grained token fallback can still be used manually."
                ),
            ),
            "reports": readiness_payload(
                READINESS_SAVED_ONLY,
                label="Saved only",
                description="Scheduled reports are stored and on-demand reports work, but recurring delivery and PDF/email jobs are not wired yet.",
            ),
            "team_invites": readiness_payload(
                READINESS_SAVED_ONLY,
                label="Saved only",
                description="Invite records are stored, but invite delivery and acceptance flows are not wired yet.",
            ),
            "webhooks": readiness_payload(
                READINESS_WORKING if webhook_delivery_available else READINESS_SETUP_REQUIRED,
                label="Outbound webhooks ready" if webhook_delivery_available else "Webhook delivery unavailable",
                description=(
                    "Outbound webhook delivery, signing, delivery history, and private-target blocking are active."
                    if webhook_delivery_available
                    else "Webhook delivery is disabled in this environment."
                ),
            ),
        },
        "report_delivery_configured": False,
        "team_invite_delivery_configured": False,
        "webhook_delivery_available": webhook_delivery_available,
    }
