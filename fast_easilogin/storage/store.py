from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any, cast

from loguru import logger
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlmodel import col, select

from fast_easilogin.storage.database import get_engine
from fast_easilogin.storage.models import (
    AppSettings,
    SettingTable,
    UserRecord,
    UserTable,
)

_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory  # noqa: PLW0603
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False)
    return _session_factory


async def _get_session() -> AsyncSession:
    return _get_session_factory()()


def _table_to_record(u: UserTable) -> UserRecord:
    """数据库模型到DTO"""
    return UserRecord(
        user_id=u.user_id,
        active=u.active,
        phone=u.phone,
        password=u.password,
        user_nickname=u.user_nickname,
        user_realname=u.user_realname,
        head_img=u.head_img,
        pt_timestamp=u.pt_timestamp,
    )


async def load_users() -> dict[str, UserRecord]:
    """加载所有用户"""
    session = await _get_session()
    try:
        result = await session.execute(select(UserTable))
        users = result.scalars().all()
        return {u.user_id: _table_to_record(u) for u in users}
    finally:
        await session.close()


async def find_user(identifier: str) -> UserRecord | None:
    """按 user_id 或手机号查找"""
    session = await _get_session()
    try:
        result = await session.execute(
            select(UserTable).where(
                or_(
                    col(UserTable.user_id) == identifier,
                    col(UserTable.phone) == identifier,
                )
            )
        )
        user = result.scalar_one_or_none()
        return _table_to_record(user) if user else None
    finally:
        await session.close()


async def save_users(users: dict[str, UserRecord], user_ids: list[str] | None = None) -> bool:
    """保存用户 (upsert)"""
    session = await _get_session()
    try:
        now = datetime.now(UTC)
        ids = set(user_ids) if user_ids is not None else None
        targets = [u for u in users.values() if ids is None or u.user_id in ids]
        for record in targets:
            existing = await session.get(UserTable, record.user_id)
            if existing:
                existing.active = record.active
                existing.phone = record.phone
                existing.password = record.password
                existing.user_nickname = record.user_nickname
                existing.user_realname = record.user_realname
                existing.head_img = record.head_img
                existing.pt_timestamp = record.pt_timestamp
                existing.updated_at = now
            else:
                session.add(UserTable(
                    user_id=record.user_id,
                    active=record.active,
                    phone=record.phone,
                    password=record.password,
                    user_nickname=record.user_nickname,
                    user_realname=record.user_realname,
                    head_img=record.head_img,
                    pt_timestamp=record.pt_timestamp,
                    created_at=now,
                    updated_at=now,
                ))
        await session.commit()
        return True
    except Exception:
        await session.rollback()
        logger.exception("保存用户失败")
        return False
    finally:
        await session.close()


async def delete_user(user_id: str) -> bool:
    """删除用户"""
    session = await _get_session()
    try:
        user = await session.get(UserTable, user_id)
        if not user:
            return False
        await session.delete(user)
        await session.commit()
        return True
    except Exception:
        await session.rollback()
        logger.exception("删除用户失败: user_id={}", user_id)
        return False
    finally:
        await session.close()


async def user_exists(user_id: str) -> bool:
    """检查用户是否存在"""
    session = await _get_session()
    try:
        return await session.get(UserTable, user_id) is not None
    finally:
        await session.close()


_DEFAULT_SETTINGS = AppSettings()


async def load_settings() -> AppSettings:
    """加载配置"""
    session = await _get_session()
    try:
        result = await session.execute(select(SettingTable))
        rows = result.scalars().all()
        kv = {r.key: r.value for r in rows}

        if not kv:
            await _write_default_settings(session)
            return _DEFAULT_SETTINGS

        global_data: dict[str, Any] = {}
        for k, v in kv.items():
            if k.startswith("global."):
                field = k.removeprefix("global.")
                try:
                    global_data[field] = json.loads(v)
                except json.JSONDecodeError:
                    logger.warning("配置值解析失败: key={} value={}", k, v)

        settings_dict = _DEFAULT_SETTINGS.model_dump()
        if global_data:
            settings_dict["Global"].update(global_data)

        return AppSettings.model_validate(settings_dict)
    finally:
        await session.close()


async def save_settings(settings: AppSettings) -> bool:
    """保存配置"""
    session = await _get_session()
    try:
        now = datetime.now(UTC)
        data = settings.model_dump()
        global_data = data.get("Global", {})

        for field, value in global_data.items():
            key = f"global.{field}"
            existing = await session.get(SettingTable, key)
            if existing:
                existing.value = json.dumps(value)
                existing.updated_at = now
            else:
                session.add(SettingTable(key=key, value=json.dumps(value), updated_at=now))

        await session.commit()
        return True
    except Exception:
        await session.rollback()
        logger.exception("保存配置失败")
        return False
    finally:
        await session.close()


async def update_settings(update_data: dict[str, Any]) -> bool:
    """部分更新配置"""
    current = await load_settings()
    current_dict = current.model_dump()

    if update_data.get("Global"):
        current_dict["Global"].update(update_data["Global"])

    updated = AppSettings.model_validate(current_dict)
    return await save_settings(updated)


async def _write_default_settings(session: AsyncSession) -> None:
    """写默认配置"""
    now = datetime.now(UTC)
    defaults = _DEFAULT_SETTINGS.model_dump()
    for field, value in defaults.get("Global", {}).items():
        session.add(SettingTable(key=f"global.{field}", value=json.dumps(value), updated_at=now))
    await session.commit()


def load_settings_sync() -> AppSettings:
    """加载配置(同步)"""
    from fast_easilogin.storage.database import init_db  # noqa: PLC0415

    async def _init_and_load() -> AppSettings:
        await init_db()
        return await load_settings()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures  # noqa: PLC0415
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, _init_and_load())
            return cast(AppSettings, future.result())
    else:
        return asyncio.run(_init_and_load())
