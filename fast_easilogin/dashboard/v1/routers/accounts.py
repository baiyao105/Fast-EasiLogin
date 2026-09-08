from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError

from fast_easilogin.application.accounts import AccountApplication
from fast_easilogin.auth.service import authenticate_user
from fast_easilogin.dashboard.v1.auth import require_dashboard_auth
from fast_easilogin.dashboard.v1.models import (
    AccountCreateRequest,
    AccountPatchRequest,
    AccountVerification,
    AccountVerifyRequest,
    DashboardAccount,
    Page,
    UpstreamUserProfile,
)
from fast_easilogin.storage.store import get_all_users, get_user, save_user

MAX_PAGE_SIZE = 100

router = APIRouter(prefix="/accounts", tags=["accounts"], dependencies=[Depends(require_dashboard_auth)])
_accounts = AccountApplication()


def _dto(user) -> DashboardAccount:
    return DashboardAccount(user_id=user.user_id, phone=user.phone, nickname=user.nick_name, real_name=user.real_name, avatar_url=user.avatar_url, active=user.active, last_login_at=user.last_login_at, created_at=user.created_at, updated_at=user.updated_at)


@router.post("/verify", response_model=AccountVerification)
async def verify(body: AccountVerifyRequest, request: Request) -> AccountVerification:
    try:
        result = await authenticate_user(request.app.state.services, body.account, body.password)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="upstream_authentication_failed") from exc
    profile = UpstreamUserProfile(user_id=result.user_id or body.account, phone=result.phone, nickname=result.nick_name or "", real_name=result.real_name, avatar_url=result.avatar_url or "")
    session_id = request.cookies.get("fast_easilogin_dashboard", "local")
    if request.app.state.services.encryptor is None:
        raise HTTPException(status_code=503, detail="credential_encryption_unavailable")
    value = _accounts.issue(session_id, body.account, body.password, profile, request.app.state.services.encryptor)
    return AccountVerification(verification_token=value.token, expires_at=value.expires_at, profile=profile)


@router.post("", response_model=DashboardAccount, status_code=201)
async def create(body: AccountCreateRequest, request: Request) -> DashboardAccount:
    session_id = request.cookies.get("fast_easilogin_dashboard", "local")
    async with request.app.state.db_factory() as db:
        try:
            user = await _accounts.create(db, session_id, body.verification_token, request.app.state.services.encryptor)
            await db.commit()
        except RuntimeError as exc:
            await db.rollback()
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            await db.rollback()
            raise HTTPException(status_code=409 if str(exc) == "account_already_exists" else 400, detail=str(exc)) from exc
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(status_code=409, detail="phone_already_exists") from exc
    return _dto(user)


@router.get("", response_model=Page[DashboardAccount])
async def list_accounts(request: Request, page: int = 1, page_size: int = 20, q: str | None = None, active: bool | None = None) -> Page[DashboardAccount]:
    if page_size > MAX_PAGE_SIZE:
        raise HTTPException(status_code=422, detail="page_size_too_large")
    async with request.app.state.db_factory() as db:
        users = await get_all_users(db)
    users = [u for u in users if (q is None or q.lower() in u.user_id.lower() or q.lower() in u.nick_name.lower()) and (active is None or u.active == active)]
    start = (page - 1) * page_size
    return Page(items=[_dto(u) for u in users[start:start + page_size]], page=page, page_size=page_size, total=len(users))


@router.get("/{user_id}", response_model=DashboardAccount)
async def get_account(user_id: str, request: Request) -> DashboardAccount:
    async with request.app.state.db_factory() as db:
        user = await get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="account_not_found")
    return _dto(user)


@router.patch("/{user_id}", response_model=DashboardAccount)
async def patch_account(user_id: str, body: AccountPatchRequest, request: Request) -> DashboardAccount:
    async with request.app.state.db_factory() as db:
        user = await get_user(db, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="account_not_found")
        if body.active is not None:
            user.active = body.active
        await save_user(db, user)
        await db.commit()
    return _dto(user)


@router.post("/{user_id}/enable", response_model=DashboardAccount)
async def enable(user_id: str, request: Request) -> DashboardAccount:
    return await patch_account(user_id, AccountPatchRequest(active=True), request)


@router.post("/{user_id}/disable", response_model=DashboardAccount)
async def disable(user_id: str, request: Request) -> DashboardAccount:
    return await patch_account(user_id, AccountPatchRequest(active=False), request)


@router.delete("/{user_id}")
async def delete(user_id: str, request: Request, confirm: bool = False) -> dict[str, bool]:
    if not confirm:
        raise HTTPException(status_code=400, detail="account_delete_confirmation_required")
    async with request.app.state.db_factory() as db:
        deleted = await _accounts.delete(db, user_id)
        await db.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail="account_not_found")
    return {"deleted": True}
