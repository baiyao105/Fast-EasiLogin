from __future__ import annotations

import contextlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from fast_easilogin.storage.models import (
    AppSettings,
    SettingTable,
    UserRecord,
    UserTable,
)


def _table_to_record(u: UserTable) -> UserRecord:
    return UserRecord(
        user_id=u.user_id,
        active=u.active,
        phone=u.phone,
        password=u.password,
        nick_name=u.nick_name,
        real_name=u.real_name,
        avatar_url=u.avatar_url,
        pt_timestamp=u.pt_timestamp,
    )


async def get_user(db: AsyncSession, user_id: str) -> UserRecord | None:
    user = await db.get(UserTable, user_id)
    return _table_to_record(user) if user else None


async def find_user(db: AsyncSession, identifier: str) -> UserRecord | None:
    result = await db.execute(
        select(UserTable).where(
            or_(
                col(UserTable.user_id) == identifier,
                col(UserTable.phone) == identifier,
            )
        )
    )
    user = result.scalar_one_or_none()
    return _table_to_record(user) if user else None


async def get_active_users(db: AsyncSession) -> list[UserRecord]:
    result = await db.execute(select(UserTable).where(col(UserTable.active) == True))  # noqa: E712
    return [_table_to_record(u) for u in result.scalars().all()]


async def get_all_users(db: AsyncSession) -> list[UserRecord]:
    result = await db.execute(select(UserTable))
    return [_table_to_record(u) for u in result.scalars().all()]


async def save_user(db: AsyncSession, record: UserRecord) -> None:
    """保存"""
    now = datetime.now(UTC)
    existing = await db.get(UserTable, record.user_id)
    if existing:
        existing.active = record.active
        existing.phone = record.phone
        existing.password = record.password
        existing.nick_name = record.nick_name
        existing.real_name = record.real_name
        existing.avatar_url = record.avatar_url
        existing.pt_timestamp = record.pt_timestamp
        existing.updated_at = now
    else:
        db.add(
            UserTable(
                user_id=record.user_id,
                active=record.active,
                phone=record.phone,
                password=record.password,
                nick_name=record.nick_name,
                real_name=record.real_name,
                avatar_url=record.avatar_url,
                pt_timestamp=record.pt_timestamp,
                created_at=now,
                updated_at=now,
            )
        )


async def delete_user(db: AsyncSession, user_id: str) -> bool:
    user = await db.get(UserTable, user_id)
    if not user:
        return False
    await db.delete(user)
    return True


async def user_exists(db: AsyncSession, user_id: str) -> bool:
    """检查用户是否存在"""
    return await db.get(UserTable, user_id) is not None


async def set_user_active(db: AsyncSession, user_id: str, active: bool) -> bool:
    user = await db.get(UserTable, user_id)
    if not user:
        return False
    user.active = active
    user.updated_at = datetime.now(UTC)
    return True


_DEFAULT_SETTINGS = AppSettings()


async def load_settings(db: AsyncSession) -> AppSettings:
    """加载配置"""
    result = await db.execute(select(SettingTable))
    rows = result.scalars().all()
    kv = {r.key: r.value for r in rows}

    if not kv:
        await _write_default_settings(db)
        return _DEFAULT_SETTINGS

    global_data: dict[str, Any] = {}
    for k, v in kv.items():
        if k.startswith("global."):
            field = k.removeprefix("global.")
            with contextlib.suppress(json.JSONDecodeError):
                global_data[field] = json.loads(v)

    settings_dict = _DEFAULT_SETTINGS.model_dump(by_alias=True)
    if global_data:
        settings_dict["Global"].update(global_data)

    return AppSettings.model_validate(settings_dict)


async def save_settings(db: AsyncSession, settings: AppSettings) -> None:
    """保存配置"""
    now = datetime.now(UTC)
    data = settings.model_dump(by_alias=True)
    global_data = data.get("Global", {})

    for field, value in global_data.items():
        key = f"global.{field}"
        existing = await db.get(SettingTable, key)
        if existing:
            existing.value = json.dumps(value)
            existing.updated_at = now
        else:
            db.add(SettingTable(key=key, value=json.dumps(value), updated_at=now))


async def update_settings(db: AsyncSession, update_data: dict[str, Any]) -> None:
    """部分更新配置"""
    current = await load_settings(db)
    current_dict = current.model_dump(by_alias=True)

    if update_data.get("Global"):
        current_dict["Global"].update(update_data["Global"])

    updated = AppSettings.model_validate(current_dict)
    await save_settings(db, updated)


async def _write_default_settings(db: AsyncSession) -> None:
    now = datetime.now(UTC)
    defaults = _DEFAULT_SETTINGS.model_dump(by_alias=True)
    for field, value in defaults.get("Global", {}).items():
        db.add(SettingTable(key=f"global.{field}", value=json.dumps(value), updated_at=now))
