"""FastAPI dependency injection — DB sessions, auth context, rate limiting."""
from fastapi import Depends, HTTPException, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError
from uuid import UUID
from typing import Optional
import redis.asyncio as aioredis
import httpx
import time
import hashlib
from datetime import datetime, timezone

from models.database import AsyncSessionLocal
from models.tables import ApiKey, User, Organization
from schemas.auth import AuthContext
from config import get_settings

settings = get_settings()


# --- Database Session ---
async def get_db() -> AsyncSession:
    """Provide an async database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# --- Redis ---
_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    """Get or create a Redis connection. Returns None if Redis is unavailable."""
    global _redis_client
    if _redis_client is None:
        try:
            client = aioredis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=1)
            await client.ping()
            _redis_client = client
        except Exception:
            return None
    return _redis_client


# --- JWT Auth ---
def _normalize_api_path(path: str) -> str:
    for prefix in ("/api/v1", "/api"):
        if path == prefix:
            return "/"
        if path.startswith(f"{prefix}/"):
            return path[len(prefix):]
    return path


def _required_scope_for_request(method: str, path: str) -> str | None:
    path = _normalize_api_path(path)
    method = method.upper()

    if path.startswith("/health"):
        return None
    if path.startswith(("/api-keys", "/auth", "/team", "/notifications", "/usage")):
        return "__jwt_only__"

    if path == "/reports/generate" and method == "POST":
        return "read:analytics"

    if path.startswith(("/analytics", "/org")):
        return "read:analytics"

    if path.startswith("/reports"):
        return "read:analytics" if method == "GET" else "write:sites"

    if path.startswith(("/sites", "/crawls", "/snippet", "/keywords", "/competitors", "/webhooks")):
        return "read:sites" if method == "GET" else "write:sites"

    if path == "/issues/root-cause-fix" and method == "POST":
        return "write:fixes"

    if path.startswith("/issues") or path.startswith("/change-log"):
        return "read:issues"

    if path.startswith("/fixes"):
        return "write:fixes" if method in {"POST", "PUT", "PATCH", "DELETE"} else "read:issues"

    return "__jwt_only__"


def _datetime_expired(value) -> bool:
    if not value:
        return False
    now = datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value < now


async def _validate_api_key(
    raw_key: str,
    request: Request,
    db: AsyncSession,
) -> AuthContext:
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    api_key = (
        await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
    ).scalar_one_or_none()
    if not api_key or _datetime_expired(api_key.expires_at):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    required_scope = _required_scope_for_request(request.method, request.url.path)
    scopes = list(api_key.scopes or [])
    if required_scope == "__jwt_only__":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires a user session, not an API key",
        )
    if required_scope and required_scope not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API key missing required scope: {required_scope}",
        )

    owner = (
        await db.execute(
            select(User)
            .where(User.org_id == api_key.org_id)
            .order_by((User.role == "owner").desc(), User.created_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not owner:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key organization has no user")

    api_key.last_used_at = datetime.now(timezone.utc)
    await db.commit()
    return AuthContext(
        user_id=owner.id,
        org_id=api_key.org_id,
        role="api_key",
        email=f"api-key:{api_key.name}",
        auth_method="api_key",
        api_key_id=api_key.id,
        scopes=scopes,
    )


async def _validate_supabase_token(token: str) -> dict:
    import os

    supabase_url = settings.SUPABASE_URL or os.environ.get("VITE_SUPABASE_URL", "")
    supabase_anon_key = settings.SUPABASE_ANON_KEY or os.environ.get("VITE_SUPABASE_ANON_KEY", "")

    if not supabase_url or not supabase_anon_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{supabase_url.rstrip('/')}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": supabase_anon_key,
                },
            )
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to validate token",
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user = response.json()
    return {
        "sub": user.get("id"),
        "email": user.get("email", ""),
        "user_metadata": user.get("user_metadata") or {},
    }


async def get_current_user(
    request: Request,
    authorization: str = Header(None),
    x_autoseo_key: str = Header(None, alias="X-AutoSEO-Key"),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    """Extract and validate JWT from Authorization header.
    
    Supports both Supabase-issued JWTs and locally-issued JWTs.
    Looks up org_id from the database when not present in the token.
    """
    if x_autoseo_key:
        return await _validate_api_key(x_autoseo_key.strip(), request, db)

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme",
        )
    if token.startswith("autoseo_"):
        return await _validate_api_key(token, request, db)

    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except JWTError:
        payload = await _validate_supabase_token(token)

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        )

    # Try to get org_id from token first (locally-issued JWTs have it)
    org_id_str = payload.get("org_id")
    role = payload.get("user_role", "member")
    email = payload.get("email", "")

    # If org_id not in token (Supabase-issued JWT), look it up in DB
    if not org_id_str:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            # Auto-provision: create org + user for new Supabase auth users
            import uuid, re
            from datetime import datetime, timezone

            email = payload.get("email", "") or payload.get("user_metadata", {}).get("email", "")
            full_name = (payload.get("user_metadata") or {}).get("full_name", "")

            def _slugify(text: str) -> str:
                slug = re.sub(r"[^\w\s-]", "", (text or "user").lower())
                return re.sub(r"[-\s]+", "-", slug).strip("-") or "user"

            base_slug = _slugify(email.split("@")[0] if email else "user")
            slug = f"{base_slug}-{str(uuid.uuid4())[:8]}"

            org = Organization(name=f"{full_name or email.split('@')[0] or 'My'}'s Organization", slug=slug, plan="free")
            db.add(org)
            await db.flush()

            user = User(
                id=user_id,
                org_id=org.id,
                role="owner",
                email=email,
                full_name=full_name or None,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        org_id = user.org_id
        role = user.role
        email = user.email
    else:
        try:
            org_id = UUID(org_id_str)
        except ValueError:
            org_id = user_id  # Fallback

    return AuthContext(
        user_id=user_id,
        org_id=org_id,
        role=role,
        email=email,
        auth_method="jwt",
    )


# --- Optional Auth ---
async def get_optional_user(
    request: Request,
    authorization: str = Header(None),
    x_autoseo_key: str = Header(None, alias="X-AutoSEO-Key"),
    db: AsyncSession = Depends(get_db),
) -> Optional[AuthContext]:
    """Like get_current_user but returns None if no auth header."""
    if not authorization and not x_autoseo_key:
        return None
    try:
        return await get_current_user(request, authorization, x_autoseo_key, db)
    except HTTPException:
        return None


# --- Rate Limiting ---
async def rate_limit(
    request: Request,
    redis: Optional[aioredis.Redis] = Depends(get_redis),
):
    """Redis sliding window rate limiter — 100 requests per minute per IP. Skipped if Redis unavailable."""
    if redis is None:
        return

    client_ip = request.client.host if request.client else "unknown"
    key = f"rate_limit:{client_ip}"
    window = 60
    max_requests = 100

    current = await redis.get(key)
    if current and int(current) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Max 100 requests per minute.",
        )

    pipe = redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, window)
    await pipe.execute()
