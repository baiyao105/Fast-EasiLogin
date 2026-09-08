from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from fastapi import HTTPException, Request

from fast_easilogin.storage.repositories.dashboard import valid_session
from fast_easilogin.storage.store import load_settings

_HASHER = PasswordHasher()
COOKIE = "fast_easilogin_dashboard"


def password_hash(password: str) -> str:
    return _HASHER.hash(password)


def password_matches(password: str, hashed: str) -> bool:
    try:
        return _HASHER.verify(hashed, password)
    except Exception:
        return False


async def password_required(request: Request) -> bool:
    async with request.app.state.db_factory() as db:
        settings = await load_settings(db)
    return request.app.state.services.dashboard_host not in {"127.0.0.1", "localhost", "::1"}


async def require_dashboard_auth(request: Request) -> None:
    if not await password_required(request):
        return
    session_id = request.cookies.get(COOKIE)
    async with request.app.state.db_factory() as db:
        if not await valid_session(db, session_id):
            raise HTTPException(status_code=401, detail="dashboard_auth_required")
        await db.commit()


def new_session(ttl: int) -> tuple[str, datetime]:
    return secrets.token_urlsafe(32), datetime.now(UTC) + timedelta(seconds=ttl)
