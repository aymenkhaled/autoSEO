"""AutoSEO API — FastAPI application entry point."""
import os
import sys

# Make the workspace root importable so `from packages.cms_adapters import …`
# resolves the same way it does inside the workers.
_WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, _WORKSPACE_ROOT)

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import structlog
import sentry_sdk

from config import get_settings
from migrations import run_startup_migrations
from models.database import engine
from dependencies import get_db
import models.tables

settings = get_settings()

# --- Sentry (only if DSN is configured) ---
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.1,
        environment=settings.ENVIRONMENT,
    )

# --- Structured Logging ---
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.ConsoleRenderer() if settings.DEBUG else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


# --- Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("AutoSEO API starting", environment=settings.ENVIRONMENT)
    await run_startup_migrations(engine, logger)
    if not settings.ANTHROPIC_API_KEY:
        from packages.shared.ai_cleanup import clear_placeholder_ai_fixes

        async for db in get_db():
            cleaned = await clear_placeholder_ai_fixes(db)
            if cleaned:
                logger.info("placeholder_ai_fixes_cleared", count=cleaned)
            break
    yield
    logger.info("AutoSEO API shutting down")
    await engine.dispose()


# --- App ---
app = FastAPI(
    title="AutoSEO API",
    version="1.0.0",
    description="Autonomous SEO Agent — Crawl, Analyze, Fix",
    lifespan=lifespan,
)

# --- CORS ---
# Bearer-token API → cookies are never sent, so wildcard is safe
# (browsers refuse `*` + credentials anyway). Override via ALLOWED_ORIGINS
# (comma-separated) to lock down in production.
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "*").strip()
if _raw_origins == "*" or not _raw_origins:
    _allow_origins = ["*"]
    _allow_credentials = False
else:
    _allow_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
    _allow_credentials = True
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["X-Request-Id"],
    max_age=600,
)


# --- Security headers (defense in depth) ---
@app.middleware("http")
async def _security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    if request.url.scheme == "https":
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response

# --- Import and register routers ---
from routers.auth import router as auth_router
from routers.sites import router as sites_router
from routers.crawls import router as crawls_router
from routers.issues import router as issues_router
from routers.fixes import router as fixes_router
from routers.connections import router as connections_router
from routers.snippet import router as snippet_router
from routers.webhooks import router as webhooks_router
from routers.analytics import router as analytics_router
from routers.dashboard import router as dashboard_router
from routers.keywords import router as keywords_router
from routers.competitors import router as competitors_router
from routers.notifications import router as notifications_router
from routers.team import router as team_router
from routers.api_keys import router as api_keys_router
from routers.usage import router as usage_router
from routers.change_log import router as change_log_router
from routers.reports import router as reports_router
from routers.system import router as system_router
from routers.github import router as github_router
from routers.search_console import router as search_console_router
from routers.google_analytics import router as google_analytics_router
from routers.pagespeed import router as pagespeed_router
from routers.indexnow import router as indexnow_router
from routers.proof import router as proof_router
from routers.autopilot import router as autopilot_router
from routers.ai_visibility import router as ai_visibility_router
from routers.content_briefs import router as content_briefs_router
from routers.crawl_budget import router as crawl_budget_router
from routers.agency import router as agency_router
from routers.integrations import router as integrations_router

_ROUTERS = [
    (auth_router, "/auth"),
    (sites_router, "/sites"),
    (connections_router, "/sites"),
    (crawls_router, "/crawls"),
    (issues_router, "/issues"),
    (fixes_router, "/fixes"),
    (snippet_router, "/snippet"),
    (webhooks_router, "/webhooks"),
    (analytics_router, "/analytics"),
    (dashboard_router, "/org"),
    (keywords_router, "/keywords"),
    (competitors_router, "/competitors"),
    (notifications_router, "/notifications"),
    (team_router, "/team"),
    (api_keys_router, "/api-keys"),
    (usage_router, "/usage"),
    (change_log_router, "/change-log"),
    (reports_router, "/reports"),
    (system_router, "/system"),
    (github_router, ""),
    (search_console_router, ""),
    (google_analytics_router, ""),
    (pagespeed_router, ""),
    (indexnow_router, ""),
    (proof_router, ""),
    (autopilot_router, ""),
    (ai_visibility_router, ""),
    (content_briefs_router, ""),
    (crawl_budget_router, ""),
    (agency_router, ""),
    (integrations_router, ""),
]

for base_prefix in ("", "/api", "/api/v1"):
    for router, route_prefix in _ROUTERS:
        app.include_router(router, prefix=f"{base_prefix}{route_prefix}")


# --- Health Check ---
@app.get("/health", tags=["system"])
async def health():
    """Health check endpoint for monitoring."""
    return {"status": "ok", "version": "1.0.0", "environment": settings.ENVIRONMENT}


@app.get("/", tags=["system"])
async def root():
    """API root — redirects to docs."""
    if frontend_dist.exists():
        return FileResponse(frontend_dist / "index.html")
    return {
        "name": "AutoSEO API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


frontend_dist = Path(__file__).resolve().parents[1] / "web" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        file_path = frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")
