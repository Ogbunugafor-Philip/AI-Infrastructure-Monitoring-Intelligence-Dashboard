"""
Database session helper for Celery tasks.

Celery workers are synchronous and (with prefork) forked, so they must NOT reuse
the FastAPI app's pooled async engine. Each task gets a fresh NullPool engine and
session, disposed at the end — safe across forks and per-task event loops.
"""
from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from config import settings


@contextlib.asynccontextmanager
async def task_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(settings.database_url_async_str, poolclass=NullPool)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with Session() as session:
            yield session
    finally:
        await engine.dispose()
