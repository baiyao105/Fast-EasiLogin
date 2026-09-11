from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from fast_easilogin.core.basic_dir import DATA_DIR, ensure_data_dir

DB_FILE = DATA_DIR / "data.db"
ASYNC_SQLITE_URL = f"sqlite+aiosqlite:///{DB_FILE}"

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine  # noqa: PLW0603
    if _engine is not None:
        return _engine
    ensure_data_dir()
    _engine = create_async_engine(
        ASYNC_SQLITE_URL,
        echo=False,
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    event.listen(_engine.sync_engine, "connect", _configure_sqlite)
    return _engine


def _configure_sqlite(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA foreign_keys=ON")
    # 轻量迁移：补齐 users 表扩展资料列 / settings.oobe_completed
    for ddl in (
        "ALTER TABLE users ADD COLUMN school TEXT",
        "ALTER TABLE users ADD COLUMN stage_name TEXT",
        "ALTER TABLE users ADD COLUMN subject_name TEXT",
        "ALTER TABLE users ADD COLUMN join_unit_time INTEGER",
        "ALTER TABLE users ADD COLUMN account_type INTEGER",
        "ALTER TABLE settings ADD COLUMN oobe_completed INTEGER DEFAULT 0",
        "ALTER TABLE settings ADD COLUMN debug_enabled INTEGER DEFAULT 0",
    ):
        try:
            cursor.execute(ddl)
        except Exception:
            pass
    cursor.close()


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory  # noqa: PLW0603
    if _session_factory is not None:
        return _session_factory
    _session_factory = async_sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False)
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession]:
    """依赖注入"""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    except BaseException:
        await session.rollback()
        raise
    finally:
        await session.close()


__all__ = ("DB_FILE", "close_db", "get_db", "get_engine", "get_session_factory", "init_db")


async def init_db() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    # logger.info("数据库初始化: {}", DB_FILE)


async def close_db() -> None:
    global _engine, _session_factory  # noqa: PLW0603
    if _session_factory is not None:
        _session_factory = None
    if _engine is not None:
        await _engine.dispose()
        _engine = None
