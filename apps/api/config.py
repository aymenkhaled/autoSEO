"""AutoSEO API Configuration — reads from environment variables."""
from pydantic_settings import BaseSettings
from pydantic import Field, model_validator
from functools import lru_cache
import os


def _make_async_url(url: str) -> str:
    """Convert a standard postgres:// URL to asyncpg format.
    
    asyncpg does not support the 'sslmode' query parameter — it uses
    ssl=True/False instead. We strip sslmode and handle SSL via connect_args.
    """
    from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Remove sslmode query param — asyncpg doesn't support it
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    query_params.pop("sslmode", None)
    new_query = urlencode({k: v[0] for k, v in query_params.items()})
    cleaned = parsed._replace(query=new_query)
    return urlunparse(cleaned)


def _make_ssl_kwargs(url: str) -> dict:
    """Extract SSL settings from original URL for asyncpg connect_args."""
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    sslmode = params.get("sslmode", ["disable"])[0]
    if sslmode in ("require", "verify-ca", "verify-full"):
        return {"ssl": True}
    return {"ssl": False}


def _make_sync_url(url: str) -> str:
    """Ensure URL uses standard postgresql:// scheme."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


class Settings(BaseSettings):
    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://autoseo:devpassword@localhost:5432/autoseo_dev"
    DATABASE_URL_SYNC: str = "postgresql://autoseo:devpassword@localhost:5432/autoseo_dev"

    # --- Supabase (optional — not required when using Replit DB) ---
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = "super-secret-jwt-token-for-local-dev-minimum-32-chars-long!!"

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Stripe ---
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_STARTER_PRICE_ID: str = "price_starter"
    STRIPE_PRO_PRICE_ID: str = "price_pro"
    STRIPE_AGENCY_PRICE_ID: str = "price_agency"

    # --- Anthropic ---
    ANTHROPIC_API_KEY: str = ""

    # --- Cloudflare R2 ---
    CLOUDFLARE_R2_ACCESS_KEY: str = ""
    CLOUDFLARE_R2_SECRET_KEY: str = ""
    CLOUDFLARE_R2_BUCKET: str = "autoseo-storage"
    CLOUDFLARE_R2_ENDPOINT: str = ""

    # --- Encryption ---
    DOPPLER_MASTER_ENCRYPTION_KEY: str = ""

    # --- ScrapFly ---
    SCRAPFLY_API_KEY: str = ""

    # --- Resend ---
    RESEND_API_KEY: str = ""

    # --- Sentry ---
    SENTRY_DSN: str = ""

    # --- GitHub App ---
    GITHUB_APP_ID: str = ""
    GITHUB_APP_PRIVATE_KEY: str = ""

    # --- App ---
    FRONTEND_URL: str = "http://localhost:5173"
    API_URL: str = "http://localhost:8001"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    model_config = {"env_file": "../../.env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @model_validator(mode="after")
    def fix_database_urls(self) -> "Settings":
        """Auto-convert DATABASE_URL to correct driver formats."""
        raw = os.environ.get("DATABASE_URL", self.DATABASE_URL)
        self.DATABASE_URL = _make_async_url(raw)
        self.DATABASE_URL_SYNC = _make_sync_url(raw)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
