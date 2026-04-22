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
from models.database import engine, Base
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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Phase 2 lightweight migrations — additive columns only
        from sqlalchemy import text
        for stmt in [
            "ALTER TABLE snippet_events ADD COLUMN IF NOT EXISTS inp_ms INTEGER",
            "ALTER TABLE snippet_events ADD COLUMN IF NOT EXISTS fcp_ms INTEGER",
            "ALTER TABLE snippet_events ADD COLUMN IF NOT EXISTS device_type TEXT",
            # Gap 5: conditional GET cache headers for pages
            "ALTER TABLE pages ADD COLUMN IF NOT EXISTS etag TEXT",
            "ALTER TABLE pages ADD COLUMN IF NOT EXISTS last_modified TEXT",
        ]:
            try:
                await conn.execute(text(stmt))
            except Exception as e:
                logger.warning("migration_skipped", stmt=stmt, error=str(e))
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
from routers.keywords import router as keywords_router
from routers.competitors import router as competitors_router
from routers.notifications import router as notifications_router
from routers.team import router as team_router
from routers.api_keys import router as api_keys_router
from routers.usage import router as usage_router
from routers.change_log import router as change_log_router

app.include_router(auth_router, prefix="/auth")
app.include_router(sites_router, prefix="/sites")
app.include_router(connections_router, prefix="/sites")
app.include_router(crawls_router, prefix="/crawls")
app.include_router(issues_router, prefix="/issues")
app.include_router(fixes_router, prefix="/fixes")
app.include_router(snippet_router, prefix="/snippet")
app.include_router(webhooks_router, prefix="/webhooks")
app.include_router(analytics_router, prefix="/analytics")
app.include_router(keywords_router, prefix="/keywords")
app.include_router(competitors_router, prefix="/competitors")
app.include_router(notifications_router, prefix="/notifications")
app.include_router(team_router, prefix="/team")
app.include_router(api_keys_router, prefix="/api-keys")
app.include_router(usage_router, prefix="/usage")
app.include_router(change_log_router, prefix="/change-log")

app.include_router(auth_router, prefix="/api/auth")
app.include_router(sites_router, prefix="/api/sites")
app.include_router(connections_router, prefix="/api/sites")
app.include_router(crawls_router, prefix="/api/crawls")
app.include_router(issues_router, prefix="/api/issues")
app.include_router(fixes_router, prefix="/api/fixes")
app.include_router(snippet_router, prefix="/api/snippet")
app.include_router(webhooks_router, prefix="/api/webhooks")
app.include_router(analytics_router, prefix="/api/analytics")
app.include_router(keywords_router, prefix="/api/keywords")
app.include_router(competitors_router, prefix="/api/competitors")
app.include_router(notifications_router, prefix="/api/notifications")
app.include_router(team_router, prefix="/api/team")
app.include_router(api_keys_router, prefix="/api/api-keys")
app.include_router(usage_router, prefix="/api/usage")
app.include_router(change_log_router, prefix="/api/change-log")


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
