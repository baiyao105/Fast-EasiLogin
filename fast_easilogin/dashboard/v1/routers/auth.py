from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

from fast_easilogin.dashboard.v1.auth import (
    COOKIE,
    new_session,
    password_hash,
    password_matches,
    password_required,
    require_dashboard_auth,
)
from fast_easilogin.dashboard.v1.models import AuthStatus, DashboardLoginRequest
from fast_easilogin.storage.repositories.dashboard import (
    create_session,
    delete_session,
    get_credential,
    save_credential,
)
from fast_easilogin.storage.store import load_settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status", response_model=AuthStatus)
async def status(request: Request) -> AuthStatus:
    required = await password_required(request)
    if not required:
        return AuthStatus(authenticated=True, password_required=False)
    try:
        await require_dashboard_auth(request)
        authenticated = True
    except HTTPException:
        authenticated = False
    return AuthStatus(authenticated=authenticated, password_required=True)


@router.post("/login", response_model=AuthStatus)
async def login(body: DashboardLoginRequest, request: Request, response: Response) -> AuthStatus:
    async with request.app.state.db_factory() as db:
        credential = await get_credential(db)
        if credential is None:
            await save_credential(db, password_hash(body.password))
            await db.commit()
        elif not password_matches(body.password, credential.password_hash):
            raise HTTPException(status_code=401, detail="invalid_dashboard_password")
        settings = await load_settings(db)
        session_id, expires = new_session(settings.global_settings.session_ttl_seconds)
        await create_session(db, session_id, expires, request.client.host if request.client else None)
        await db.commit()
    response.set_cookie(COOKIE, session_id, httponly=True, secure=request.url.hostname not in {"localhost", "127.0.0.1"}, samesite="lax", expires=expires)
    return AuthStatus(authenticated=True, password_required=True)


@router.post("/logout", response_model=AuthStatus)
async def logout(request: Request, response: Response) -> AuthStatus:
    async with request.app.state.db_factory() as db:
        await delete_session(db, request.cookies.get(COOKIE))
        await db.commit()
    response.delete_cookie(COOKIE)
    return AuthStatus(authenticated=not await password_required(request), password_required=await password_required(request))
