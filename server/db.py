from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from server.config import settings


def get_engine() -> AsyncEngine:
    if not getattr(settings, "database_url", None):
        raise RuntimeError("DATABASE_URL 未设置，请在 .env 中配置 PostgreSQL 连接串。")
    return create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)


engine = get_engine()

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """
    仅做连通性检查。

    表结构由 Alembic 管理（推荐在启动服务前执行：`alembic upgrade head`）。
    """
    async with engine.begin():
        return


@asynccontextmanager
async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
