"""
Async SQLAlchemy engine + session management for PostgreSQL.

Connects via asyncpg using the URL derived from the discrete DATABASE_* settings
in ``config.py`` (which loads them from .env). A declarative ``Base`` is exposed
for all ORM models.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config import settings


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


# Async engine bound to PostgreSQL via asyncpg.
engine = create_async_engine(
    settings.database_url_async_str,
    echo=False,                 # never echo SQL (avoids leaking data) in production
    pool_pre_ping=True,         # transparently recover dropped connections
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
)

# Session factory — expire_on_commit=False keeps objects usable after commit.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a transactional async session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
