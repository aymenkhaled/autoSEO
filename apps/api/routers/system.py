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
    gsc_configured = bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)
    ga4_configured = bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)
    serp_configured = bool(settings.DATAFORSEO_LOGIN and settings.DATAFORSEO_PASSWORD) or bool(settings.SERPAPI_API_KEY)
    stripe_configured = bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_WEBHOOK_SECRET)
    webhook_delivery_available = True

    return {
        "auth_mode": auth_mode,
        "providers": {
            "supabase": auth_mode == "supabase",
            "anthropic": ai_configured,
            "github_app": github_app_configured,
            "google_search_console": gsc_configured,
            "google_analytics": ga4_configured,
            "pagespeed": True,
            "indexnow": True,
            "stripe": stripe_configured,
            "resend": bool(settings.RESEND_API_KEY),
            "serp_provider": serp_configured,
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
            "search_console": readiness_payload(
                READINESS_WORKING if gsc_configured else READINESS_SETUP_REQUIRED,
                label="Search Console OAuth ready" if gsc_configured else "Google OAuth setup required",
                description=(
                    "Google Search Console read-only OAuth is configured for traffic, query, sitemap, and URL inspection sync."
                    if gsc_configured
                    else "Configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET before users can connect Search Console properties."
                ),
            ),
            "google_analytics": readiness_payload(
                READINESS_WORKING if ga4_configured else READINESS_SETUP_REQUIRED,
                label="GA4 OAuth ready" if ga4_configured else "Google OAuth setup required",
                description=(
                    "Google Analytics read-only OAuth is configured for sessions, key events, transactions, and revenue sync."
                    if ga4_configured
                    else "Configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET before users can connect GA4 revenue and conversion data."
                ),
            ),
            "pagespeed": readiness_payload(
                READINESS_WORKING,
                label="PageSpeed checks available",
                description="PageSpeed Insights can run without a key for light usage; configure GOOGLE_PAGESPEED_API_KEY and GOOGLE_CRUX_API_KEY for better quota and CrUX checks.",
            ),
            "indexnow": readiness_payload(
                READINESS_WORKING,
                label="IndexNow available",
                description="AutoSEO can generate IndexNow key-file instructions and submit verified changed URLs to the configured IndexNow endpoint.",
            ),
            "reports": readiness_payload(
                READINESS_WORKING if settings.RESEND_API_KEY else READINESS_SAVED_ONLY,
                label="Digest delivery ready" if settings.RESEND_API_KEY else "Digest preview only",
                description=(
                    "Resend is configured for scheduled digest delivery. Digest preview is also available in-app."
                    if settings.RESEND_API_KEY
                    else "Scheduled reports are stored and digest preview works in-app, but email delivery waits for RESEND_API_KEY."
                ),
            ),
            "proof_loop": readiness_payload(
                READINESS_WORKING,
                label="Proof loop available",
                description="AutoSEO can snapshot crawl, GSC, GA4, PageSpeed, and GitHub PR status before and after fixes.",
            ),
            "autopilot": readiness_payload(
                READINESS_WORKING,
                label="Autopilot next actions available",
                description="Autopilot can rank next actions across crawler issues, GSC, GA4, PageSpeed, IndexNow, and proof state.",
            ),
            "ai_visibility": readiness_payload(
                "readiness_scoring_only",
                label="AI answer-readiness scoring available",
                description="Manual prompt scoring works from crawled content and schema. AutoSEO does not yet query ChatGPT, Perplexity, Gemini, or Google AI Overviews.",
            ),
            "serp_keywords": readiness_payload(
                "provider_not_wired" if serp_configured else READINESS_UNAVAILABLE_WITHOUT_PROVIDER,
                label="SERP provider credentials present, sync not wired" if serp_configured else "SERP provider needed",
                description=(
                    "SERP provider credentials are present, but live rank sync is not implemented yet. Use CSV ranking import today."
                    if serp_configured
                    else "Manual CSV ranking import works now. Live rank tracking needs DataForSEO or SerpApi credentials."
                ),
            ),
            "crawl_budget": readiness_payload(
                READINESS_WORKING,
                label="Log import available",
                description="Server log imports can compare Googlebot behavior with AutoSEO crawl coverage and GSC page value.",
            ),
            "agency": readiness_payload(
                READINESS_WORKING,
                label="Agency client workspaces available",
                description="Agencies can group sites by client and use snapshot-safe report links for proof-of-work views.",
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
        "report_delivery_configured": bool(settings.RESEND_API_KEY),
        "team_invite_delivery_configured": False,
        "webhook_delivery_available": webhook_delivery_available,
    }
