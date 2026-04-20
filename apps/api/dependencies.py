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

from models.database import AsyncSessionLocal
from models.tables import User, Organization
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
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    """Extract and validate JWT from Authorization header.
    
    Supports both Supabase-issued JWTs and locally-issued JWTs.
    Looks up org_id from the database when not present in the token.
    """
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

            org = Organization(name=f"{full_name or email.split('@')[0] or 'My'}'s Organization", slug=slug, plan="starter")
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
    )


# --- Optional Auth ---
async def get_optional_user(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Optional[AuthContext]:
    """Like get_current_user but returns None if no auth header."""
    if not authorization:
        return None
    try:
        return await get_current_user(authorization, db)
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
