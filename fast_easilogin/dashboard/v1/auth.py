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


LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1", "0000:0000:0000:0000:0000:0000:0000:0001"}


async def password_required(request: Request) -> bool:
    async with request.app.state.db_factory() as db:
        settings = await load_settings(db)
    g = settings.global_settings
    host = (g.dashboard_host or "").strip().lower()
    # 非回环监听：强制要求密码
    if host and host not in LOOPBACK_HOSTS:
        return True
    # 本机监听：用户可选开启密码
    return bool(g.dashboard_password_required)


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
