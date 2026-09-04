from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.dialects.sqlite import insert
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
    """使用数据库冲突处理保存用户"""
    now = datetime.now(UTC)
    values = {
        "user_id": record.user_id,
        "active": record.active,
        "phone": record.phone or None,
        "password": record.password,
        "nick_name": record.nick_name,
        "real_name": record.real_name,
        "avatar_url": record.avatar_url,
        "pt_timestamp": record.pt_timestamp,
        "created_at": now,
        "updated_at": now,
    }
    statement = insert(UserTable).values(**values)
    statement = statement.on_conflict_do_update(
        index_elements=[UserTable.user_id],
        set_={
            "active": statement.excluded.active,
            "phone": statement.excluded.phone,
            "password": statement.excluded.password,
            "nick_name": statement.excluded.nick_name,
            "real_name": statement.excluded.real_name,
            "avatar_url": statement.excluded.avatar_url,
            "pt_timestamp": statement.excluded.pt_timestamp,
            "updated_at": now,
        },
    )
    await db.execute(statement)


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


async def load_settings(db: AsyncSession) -> AppSettings:
    """加载配置"""
    row = await db.get(SettingTable, 1)
    if row is None:
        row = SettingTable()

    return AppSettings.model_validate(
        {
            "Global": {
                "port": row.port,
                "webui_port": row.webui_port,
                "enable_eventlog": row.enable_eventlog,
                "auto_restart_on_crash": row.auto_restart_on_crash,
                "restart_delay_seconds": row.restart_delay_seconds,
                "cache_max_entries": row.cache_max_entries,
                "enable_password_error_disable": row.enable_password_error_disable,
            }
        }
    )


async def save_settings(db: AsyncSession, settings: AppSettings) -> None:
    """保存配置"""
    now = datetime.now(UTC)
    global_data = settings.global_settings
    row = await db.get(SettingTable, 1)
    if row is None:
        row = SettingTable()
        db.add(row)

    row.port = global_data.port
    row.webui_port = global_data.webui_port
    row.enable_eventlog = global_data.enable_eventlog
    row.auto_restart_on_crash = global_data.auto_restart_on_crash
    row.restart_delay_seconds = global_data.restart_delay_seconds
    row.cache_max_entries = global_data.cache_max_entries
    row.enable_password_error_disable = global_data.enable_password_error_disable
    row.updated_at = now


async def update_settings(db: AsyncSession, update_data: dict[str, Any]) -> None:
    """部分更新配置"""
    current = await load_settings(db)
    current_dict = current.model_dump(by_alias=True)

    if update_data.get("Global"):
        current_dict["Global"].update(update_data["Global"])

    updated = AppSettings.model_validate(current_dict)
    await save_settings(db, updated)
