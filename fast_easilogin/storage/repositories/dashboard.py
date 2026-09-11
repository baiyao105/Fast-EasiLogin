from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from fast_easilogin.storage.models import DashboardCredentialTable, DashboardSessionTable


async def get_credential(db: AsyncSession) -> DashboardCredentialTable | None:
    return await db.get(DashboardCredentialTable, 1)


async def save_credential(db: AsyncSession, password_hash: str) -> None:
    row = await get_credential(db)
    if row is None:
        db.add(DashboardCredentialTable(password_hash=password_hash))
    else:
        row.password_hash = password_hash
        row.updated_at = datetime.now(UTC)


async def create_session(db: AsyncSession, session_id: str, expires_at: datetime, remote_address: str | None) -> None:
    now = datetime.now(UTC)
    db.add(
        DashboardSessionTable(
            id=session_id, created_at=now, last_seen_at=now, expires_at=expires_at, remote_address=remote_address
        )
    )


async def valid_session(db: AsyncSession, session_id: str | None) -> bool:
    if not session_id:
        return False
    row = await db.get(DashboardSessionTable, session_id)
    if row is None:
        return False
    expires_at = row.expires_at.replace(tzinfo=UTC) if row.expires_at.tzinfo is None else row.expires_at
    if expires_at <= datetime.now(UTC):
        if row is not None:
            await db.delete(row)
        return False
    row.last_seen_at = datetime.now(UTC)
    return True


async def delete_session(db: AsyncSession, session_id: str | None) -> None:
    if session_id:
        await db.execute(delete(DashboardSessionTable).where(col(DashboardSessionTable.id) == session_id))
