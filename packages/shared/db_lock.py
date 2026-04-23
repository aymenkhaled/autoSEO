"""Database advisory locks used for coarse cross-worker coordination."""
from __future__ import annotations

import hashlib
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


def advisory_lock_key(namespace: str, value: str) -> int:
    digest = hashlib.blake2b(f"{namespace}:{value}".encode("utf-8"), digest_size=8).digest()
    unsigned = int.from_bytes(digest, byteorder="big", signed=False)
    return unsigned - (1 << 64) if unsigned >= (1 << 63) else unsigned


@asynccontextmanager
async def advisory_lock(engine: AsyncEngine, namespace: str, value: str):
    """Hold a Postgres advisory lock for the lifetime of the context."""
    key = advisory_lock_key(namespace, value)
    async with engine.connect() as conn:
        acquired = bool(
            (
                await conn.execute(
                    text("SELECT pg_try_advisory_lock(:key)"),
                    {"key": key},
                )
            ).scalar()
        )
        try:
            yield acquired
        finally:
            if acquired:
                await conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
                await conn.commit()
