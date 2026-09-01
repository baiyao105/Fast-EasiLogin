from __future__ import annotations

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel

from fast_easilogin.core.basic_dir import DATA_DIR, ensure_data_dir

DB_FILE = DATA_DIR / "data.db"
ASYNC_SQLITE_URL = f"sqlite+aiosqlite:///{DB_FILE}"

_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    """全局引擎"""
    global _engine  # noqa: PLW0603
    if _engine is not None:
        return _engine
    ensure_data_dir()
    _engine = create_async_engine(
        ASYNC_SQLITE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    return _engine


async def init_db() -> None:
    """init"""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    # logger.info("数据库初始化: {}", DB_FILE)


async def close_db() -> None:
    """关引擎"""
    global _engine  # noqa: PLW0603
    if _engine is not None:
        await _engine.dispose()
        _engine = None
