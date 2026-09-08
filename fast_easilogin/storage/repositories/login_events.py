from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from fast_easilogin.storage.models import LoginEventTable


async def record_login_event(
    db: AsyncSession,
    *,
    username: str,
    status: str,
    user_id: str | None = None,
    error_code: str | None = None,
    ip_address: str = "",
) -> LoginEventTable:
    event = LoginEventTable(
        username=username,
        user_id=user_id,
        status=status,
        error_code=error_code,
        ip_address=ip_address,
    )
    db.add(event)
    await db.flush()
    return event


async def list_login_events(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    user_id: str | None = None,
) -> tuple[list[LoginEventTable], int]:
    filters = []
    if status:
        filters.append(LoginEventTable.status == status)
    if user_id:
        filters.append(LoginEventTable.user_id == user_id)
    total = int((await db.scalar(select(func.count()).select_from(LoginEventTable).where(*filters))) or 0)
    statement = (
        select(LoginEventTable)
        .where(*filters)
        .order_by(cast(Any, LoginEventTable.created_at).desc(), cast(Any, LoginEventTable.id).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list((await db.execute(statement)).scalars().all()), total


async def summarize_login_events(db: AsyncSession, *, since: datetime | None = None) -> dict[str, int]:
    filters = [LoginEventTable.created_at >= since] if since else []
    rows = await db.execute(
        select(LoginEventTable.status, func.count()).where(*filters).group_by(LoginEventTable.status)
    )
    return {status: int(count) for status, count in rows.all()}


async def trend_login_events(db: AsyncSession, *, since: datetime, hours: int = 24) -> list[dict[str, int | str]]:
    events, _ = await list_login_events(db, page=1, page_size=10000)
    buckets: dict[str, int] = {}
    for event in events:
        created_at = event.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if created_at < since:
            continue
        key = created_at.astimezone(UTC).strftime("%Y-%m-%d %H:00")
        buckets[key] = buckets.get(key, 0) + 1
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    return [
        {
            "time": (now - timedelta(hours=offset)).isoformat(),
            "count": buckets.get((now - timedelta(hours=offset)).strftime("%Y-%m-%d %H:00"), 0),
        }
        for offset in range(hours - 1, -1, -1)
    ]


async def prune_login_events(db: AsyncSession, *, before: datetime) -> int:
    result = await db.execute(
        delete(LoginEventTable)
        .where(cast(Any, LoginEventTable.created_at) < before.replace(tzinfo=None))
        .execution_options(synchronize_session=False)
    )
    return int(getattr(result, "rowcount", 0) or 0)
