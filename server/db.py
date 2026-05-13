from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from server.config import settings


def get_engine() -> AsyncEngine:
    url = getattr(settings, "database_url", None)
    if not url:
        url = "sqlite+aiosqlite:///./dev.db"
    return create_async_engine(url, echo=False, pool_pre_ping=True)


engine = get_engine()

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """
    仅做连通性检查。

    表结构由 Alembic 管理（推荐在启动服务前执行：`alembic upgrade head`）。
    """
    async with engine.begin():
        return


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
