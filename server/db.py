from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from server.config import settings


def get_engine() -> AsyncEngine:
    return create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)


engine = get_engine()
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def reset_engine(url: str) -> None:
    global engine, AsyncSessionLocal
    settings.database_url = url
    engine = create_async_engine(url, echo=False, pool_pre_ping=True)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """
    仅做连通性检查。

    表结构由 Alembic 管理（推荐在启动服务前执行：`alembic upgrade head`）。
    """
    try:
        async with engine.begin() as conn:
            if engine.url.drivername.startswith("sqlite"):
                await conn.run_sync(SQLModel.metadata.create_all)
            return
    except Exception:
        if not engine.url.drivername.startswith("sqlite"):
            reset_engine("sqlite+aiosqlite:///./dev.db")
            async with engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)
            return
        raise


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
