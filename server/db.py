from __future__ import annotations

from sqlalchemy.engine import make_url
from sqlalchemy.dialects.sqlite import dialect as sqlite_dialect
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from server.config import settings
from server.logging_utils import get_logger

logger = get_logger(__name__)


def _mask_db_url(url: str) -> str:
    try:
        return make_url(url).render_as_string(hide_password=True)
    except Exception:
        return url


def get_engine() -> AsyncEngine:
    logger.info("create engine driver=%s host=%s port=%s db=%s", "postgresql+asyncpg", settings.db_host, settings.db_port, settings.db_name)
    return create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)


engine = get_engine()
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def reset_engine(url: str) -> None:
    global engine, AsyncSessionLocal
    settings.set_database_url_override(url)
    logger.warning("reset engine to %s", url)
    engine = create_async_engine(url, echo=False, pool_pre_ping=True)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _ensure_sqlite_columns(conn) -> None:
    if not engine.url.drivername.startswith("sqlite"):
        return
    d = sqlite_dialect()
    for table in SQLModel.metadata.sorted_tables:
        name = table.name
        try:
            res = await conn.exec_driver_sql(f"PRAGMA table_info('{name}')")
        except Exception:
            continue
        rows = res.fetchall()
        existing = {r[1] for r in rows}
        for col in table.columns:
            col_name = col.name
            if col_name in existing:
                continue
            try:
                col_type = col.type
                if col_type.__class__.__name__ in {"JSON", "JSONB"}:
                    ddl_type = "TEXT"
                else:
                    ddl_type = col_type.compile(dialect=d)
            except Exception:
                ddl_type = "TEXT"
            await conn.exec_driver_sql(f'ALTER TABLE "{name}" ADD COLUMN "{col_name}" {ddl_type}')


async def init_db() -> None:
    """
    仅做连通性检查。

    表结构由 Alembic 管理（推荐在启动服务前执行：`alembic upgrade head`）。
    """
    try:
        logger.info("init db start: %s", _mask_db_url(settings.database_url))
        async with engine.begin() as conn:
            if engine.url.drivername.startswith("sqlite"):
                try:
                    await conn.run_sync(SQLModel.metadata.create_all)
                except Exception as e:
                    if "already exists" not in str(e):
                        raise
                await _ensure_sqlite_columns(conn)
                logger.info("sqlite schema ensured")
            else:
                logger.info("database connection ok: %s", engine.url)
            return
    except Exception as e:
        logger.exception("database init failed, driver=%s, error=%s", engine.url.drivername, e)
        if not engine.url.drivername.startswith("sqlite"):
            logger.warning("fallback to local sqlite dev.db")
            reset_engine("sqlite+aiosqlite:///./dev.db")
            async with engine.begin() as conn:
                try:
                    await conn.run_sync(SQLModel.metadata.create_all)
                except Exception as e:
                    if "already exists" not in str(e):
                        raise
                await _ensure_sqlite_columns(conn)
            logger.info("sqlite fallback ready")
            return
        raise



async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
