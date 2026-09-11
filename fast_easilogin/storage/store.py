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
from fast_easilogin.storage.repositories.accounts import delete_credentials


def _table_to_record(u: UserTable) -> UserRecord:
    return UserRecord(
        user_id=u.user_id,
        active=u.active,
        phone=u.phone,
        password="",
        nick_name=u.nick_name,
        real_name=u.real_name,
        avatar_url=u.avatar_url,
        pt_timestamp=u.pt_timestamp,
        last_login_at=u.last_login_at,
        created_at=u.created_at,
        updated_at=u.updated_at,
        school=getattr(u, "school", None),
        stage_name=getattr(u, "stage_name", None),
        subject_name=getattr(u, "subject_name", None),
        join_unit_time=getattr(u, "join_unit_time", None),
        account_type=getattr(u, "account_type", None),
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
        "nick_name": record.nick_name,
        "real_name": record.real_name,
        "avatar_url": record.avatar_url,
        "pt_timestamp": record.pt_timestamp,
        "school": getattr(record, "school", None),
        "stage_name": getattr(record, "stage_name", None),
        "subject_name": getattr(record, "subject_name", None),
        "join_unit_time": getattr(record, "join_unit_time", None),
        "account_type": getattr(record, "account_type", None),
        "last_login_at": getattr(record, "last_login_at", None),
        "created_at": getattr(record, "created_at", None) or now,
        "updated_at": now,
    }
    statement = insert(UserTable).values(**values)
    statement = statement.on_conflict_do_update(
        index_elements=[UserTable.user_id],
        set_={
            "active": statement.excluded.active,
            "phone": statement.excluded.phone,
            "nick_name": statement.excluded.nick_name,
            "real_name": statement.excluded.real_name,
            "avatar_url": statement.excluded.avatar_url,
            "pt_timestamp": statement.excluded.pt_timestamp,
            "school": statement.excluded.school,
            "stage_name": statement.excluded.stage_name,
            "subject_name": statement.excluded.subject_name,
            "join_unit_time": statement.excluded.join_unit_time,
            "account_type": statement.excluded.account_type,
            "last_login_at": statement.excluded.last_login_at,
            "updated_at": now,
        },
    )
    await db.execute(statement)


async def delete_user(db: AsyncSession, user_id: str) -> bool:
    user = await db.get(UserTable, user_id)
    if not user:
        return False
    # 先删子表凭据，避免 users 外键约束冲突
    await delete_credentials(db, user_id)
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


async def touch_user_login(db: AsyncSession, user_id: str) -> bool:
    """真实登录成功后刷新最近活跃时间。"""
    user = await db.get(UserTable, user_id)
    if not user:
        return False
    now = datetime.now(UTC)
    user.last_login_at = now
    user.updated_at = now
    return True


async def update_user_profile(
    db: AsyncSession,
    user_id: str,
    *,
    nick_name: str | None = None,
    real_name: str | None = None,
    avatar_url: str | None = None,
    phone: str | None = None,
    school: str | None = None,
    stage_name: str | None = None,
    subject_name: str | None = None,
    join_unit_time: int | None = None,
    account_type: int | None = None,
) -> bool:
    user = await db.get(UserTable, user_id)
    if not user:
        return False
    if nick_name is not None:
        user.nick_name = nick_name
    if real_name is not None:
        user.real_name = real_name
    if avatar_url is not None:
        user.avatar_url = avatar_url
    if phone is not None:
        user.phone = phone
    if school is not None:
        user.school = school
    if stage_name is not None:
        user.stage_name = stage_name
    if subject_name is not None:
        user.subject_name = subject_name
    if join_unit_time is not None:
        user.join_unit_time = join_unit_time
    if account_type is not None:
        user.account_type = account_type
    user.updated_at = datetime.now(UTC)
    return True


async def load_settings(db: AsyncSession) -> AppSettings:
    """加载配置"""
    row = await db.get(SettingTable, 1)
    if row is None:
        return AppSettings()

    return AppSettings.model_validate(
        {
            "Global": {
                "port": row.port,
                "webui_port": row.webui_port,
                "dashboard_host": row.dashboard_host,
                "enable_eventlog": row.enable_eventlog,
                "auto_restart_on_crash": row.auto_restart_on_crash,
                "restart_delay_seconds": row.restart_delay_seconds,
                "cache_max_entries": row.cache_max_entries,
                "enable_password_error_disable": row.enable_password_error_disable,
                "dashboard_password_required": row.dashboard_password_required,
                "session_ttl_seconds": row.session_ttl_seconds,
                "encryption_key_source": row.encryption_key_source,
                "encryption_key_version": row.encryption_key_version,
            }
        }
    )


async def initialize_settings(db: AsyncSession) -> AppSettings:
    row = await db.get(SettingTable, 1)
    if row is None:
        row = SettingTable()
        db.add(row)
        await db.flush()
    return AppSettings.model_validate(
        {
            "Global": {
                "port": row.port,
                "webui_port": row.webui_port,
                "dashboard_host": row.dashboard_host,
                "enable_eventlog": row.enable_eventlog,
                "auto_restart_on_crash": row.auto_restart_on_crash,
                "restart_delay_seconds": row.restart_delay_seconds,
                "cache_max_entries": row.cache_max_entries,
                "enable_password_error_disable": row.enable_password_error_disable,
                "dashboard_password_required": row.dashboard_password_required,
                "session_ttl_seconds": row.session_ttl_seconds,
                "encryption_key_source": row.encryption_key_source,
                "encryption_key_version": row.encryption_key_version,
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
    row.dashboard_host = global_data.dashboard_host
    row.enable_eventlog = global_data.enable_eventlog
    row.auto_restart_on_crash = global_data.auto_restart_on_crash
    row.restart_delay_seconds = global_data.restart_delay_seconds
    row.cache_max_entries = global_data.cache_max_entries
    row.enable_password_error_disable = global_data.enable_password_error_disable
    row.dashboard_password_required = global_data.dashboard_password_required
    row.session_ttl_seconds = global_data.session_ttl_seconds
    row.encryption_key_source = global_data.encryption_key_source
    row.encryption_key_version = global_data.encryption_key_version
    row.updated_at = now


async def update_settings(db: AsyncSession, update_data: dict[str, Any]) -> None:
    """部分更新配置"""
    current = await load_settings(db)
    current_dict = current.model_dump(by_alias=True)

    if update_data.get("Global"):
        current_dict["Global"].update(update_data["Global"])

    updated = AppSettings.model_validate(current_dict)
    await save_settings(db, updated)
