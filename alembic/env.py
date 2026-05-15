from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

# 读取 .env（Pydantic Settings），避免 alembic 运行时未加载环境变量导致误连 postgres
from server.config import settings

# 导入 models，确保 SQLModel.metadata 包含所有表
from server import models  # noqa: F401
from server.marketing import models as marketing_models  # noqa: F401


# this is the Alembic Config object, which provides access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def get_database_url() -> str:
    # 统一使用 settings 里根据 DB_HOST/DB_PORT/DB_NAME/DB_USERNAME/DB_PASSWORD 组装的连接串
    url = getattr(settings, "database_url", None)
    if not url:
        raise RuntimeError("数据库配置未设置，请检查 .env 中的 DB_HOST/DB_PORT/DB_NAME/DB_USERNAME/DB_PASSWORD")
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
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


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode (async engine)."""
    url = get_database_url()
    connectable = create_async_engine(url, poolclass=pool.NullPool)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
