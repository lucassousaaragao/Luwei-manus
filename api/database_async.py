import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from api.db_models import Base

# Database URL from environment or default to SQLite for development
raw_db_url = os.environ.get(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./data/luwei.db"
)

# For PostgreSQL, use: postgresql+asyncpg://user:pass@host:port/db
# For SQLite, use: sqlite+aiosqlite:///./data/luwei.db

DATABASE_URL = raw_db_url
if DATABASE_URL.startswith("sqlite"):
    # Add timeout for busy waiting on SQLite locks
    if "?" not in DATABASE_URL:
        DATABASE_URL += "?timeout=30"
    elif "timeout=" not in DATABASE_URL:
        DATABASE_URL += "&timeout=30"

engine = create_async_engine(
    DATABASE_URL,
    echo=os.environ.get("SQL_ECHO", "false").lower() == "true",
    poolclass=NullPool if "sqlite" in DATABASE_URL else None,
    pool_pre_ping=True,
    **({} if "sqlite" in DATABASE_URL else {"pool_size": 10, "max_overflow": 20}),
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Enable WAL mode for SQLite to improve concurrency
    if "sqlite" in DATABASE_URL:
        async with engine.connect() as conn:
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.commit()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database session outside FastAPI."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
