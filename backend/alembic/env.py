"""Alembic async migration environment.

Uses the asyncpg URL derived in config.py (from .env) and the metadata of all
ORM models. No credentials are written to alembic.ini.
"""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from config import settings
from database import Base
import models  # noqa: F401  (imported for side effect: registers all tables)

config = context.config

# NB: we deliberately do NOT push the URL into alembic's ini via
# set_main_option — the URL-encoded password contains '%' which configparser
# would misread as interpolation syntax. The async engine is built directly
# from settings instead (see run_async_migrations).

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url_async_str,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(
        settings.database_url_async_str,
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
