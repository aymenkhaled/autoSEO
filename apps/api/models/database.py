"""SQLAlchemy async database engine and session factory."""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import get_settings, _make_ssl_kwargs
import os

settings = get_settings()

# Build connect_args for asyncpg (handles SSL properly)
_raw_db_url = os.environ.get("DATABASE_URL", "")
_connect_args = _make_ssl_kwargs(_raw_db_url)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass
