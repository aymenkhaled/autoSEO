from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = PROJECT_ROOT / "apps" / "api"

if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

os.environ.setdefault("DATABASE_URL", "postgresql://autoseo:devpassword@localhost:5432/autoseo_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/2")
os.environ.setdefault("SUPABASE_JWT_SECRET", "super-secret-jwt-token-for-local-dev-minimum-32-chars-long!!")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("ANTHROPIC_API_KEY", "")

from config import get_settings

get_settings.cache_clear()

import models.tables  # noqa: F401
from models.database import AsyncSessionLocal, Base, engine


async def _recreate_schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


async def _truncate_all():
    table_names = [table.name for table in Base.metadata.sorted_tables]
    if not table_names:
        await engine.dispose()
        return
    joined = ", ".join(f'"{name}"' for name in reversed(table_names))
    async with AsyncSessionLocal() as session:
        await session.execute(text(f"TRUNCATE TABLE {joined} RESTART IDENTITY CASCADE"))
        await session.commit()
    await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def prepare_test_database():
    asyncio.run(_recreate_schema())
    yield
    asyncio.run(_recreate_schema())


@pytest.fixture(autouse=True)
def clean_database(prepare_test_database):
    asyncio.run(_truncate_all())
    yield
    asyncio.run(_truncate_all())
