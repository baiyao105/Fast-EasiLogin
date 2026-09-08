from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from fast_easilogin.auth.service import (
    authenticate_user as user_login,
)
from fast_easilogin.auth.service import (
    fetch_user_info,
)
from fast_easilogin.auth.service import (
    get_user_info as get_aggregated_user_info,
)
from fast_easilogin.core.constants import TOKEN_OFFLINE_SUFFIX
from fast_easilogin.core.services import Services
from fast_easilogin.storage import get_db
from fast_easilogin.storage.database import get_session_factory
from fast_easilogin.storage.models import (
    AppSaveDataBody,
    DataResponse,
    OkResponse,
    SaveUserBody,
    UserInfoRequest,
    UserRecord,
)
from fast_easilogin.storage.repositories.accounts import save_credentials
from fast_easilogin.storage.store import (
    find_user,
    get_active_users,
    get_user,
    save_user,
)

router = APIRouter()


def _get_services(request: Request) -> Services:
    return request.app.state.services


def ok_response(data: dict | list | None = None) -> dict:
    r: dict = {"message": "success", "statusCode": "200"}
    if data is not None:
        r["data"] = data
    return r


async def _update_user_profile(
    services: Services,
    uid: str,
    token: str,
    nickname: str | None = None,
    avatar_url: str | None = None,
) -> None:
    """后台任务"""
    state = services.state
    acquired = await state.acquire_inflight(uid)
    if not acquired:
        return
    factory = get_session_factory()
    async with factory() as db:
        try:
            rec = await get_user(db, uid)
            if not rec:
                return
            fetched = await fetch_user_info(services, token)
            if not fetched:
                return
            new_name = fetched.get("nickName") or nickname or rec.nick_name
            new_img = fetched.get("photoUrl") or avatar_url or rec.avatar_url
            real_name = fetched.get("realName") or rec.real_name or ""
            changed = (
                (new_name or "") != (rec.nick_name or "")
                or (real_name or "") != (rec.real_name or "")
                or (new_img or "") != (rec.avatar_url or "")
            )
            if not changed:
                return
            rec.nick_name = new_name or ""
            rec.real_name = real_name
            rec.avatar_url = new_img or ""
            await save_user(db, rec)
            await db.commit()
            logger.success(
                "账户信息被更新: usrid({}) {}",
                uid,
                {"nick_name": new_name, "real_name": real_name, "avatar_url": new_img},
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            await db.rollback()
            logger.exception("更新用户资料异常: uid={}", uid)
        finally:
            await state.release_inflight(uid)


SaveBody = Annotated[SaveUserBody | AppSaveDataBody, "body"]


@router.get("/savedata", response_model=OkResponse)
async def savedata():
    return ok_response()


@router.post("/user/info", response_model=DataResponse)
async def user_info(
    body: UserInfoRequest,
    request: Request,
    services: Services = Depends(_get_services),
    db: AsyncSession = Depends(get_db),
):
    logger.info("聚合用户信息: user_id={} fields_count={}", body.user_id, len(body.fields or []))
    data = await get_aggregated_user_info(services, db, body.user_id, body.password, body.fields)
    return ok_response(data)


@router.get("/getData/SSOLOGIN", response_model=DataResponse)
async def get_sso_list(
    pt_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    users = await get_active_users(db)
    data: list[dict[str, str]] = [
        {
            "pt_nickname": u.nick_name,
            "pt_appid": u.user_id,
            "pt_userid": u.user_id,
            "pt_username": u.real_name or u.user_id,
            "pt_photourl": u.avatar_url,
        }
        for u in users
    ]
    return ok_response(data)


@router.get("/getData/SSOLOGIN/{userid}", response_model=OkResponse)
async def sso_login_user(  # noqa: PLR0917
    userid: str,
    response: Response,
    request: Request,
    background_tasks: BackgroundTasks,
    services: Services = Depends(_get_services),
    db: AsyncSession = Depends(get_db),
):
    record = await find_user(db, userid)
    if record is None or not record.active:
        raise HTTPException(status_code=404, detail={"message": "user_not_found", "statusCode": "404"})
    login_account = record.phone or userid
    token_info = await user_login(services, login_account, None, userid_for_disable=record.user_id)
    token = str(token_info.token)
    response.set_cookie(
        key="pt_token",
        value=token,
        domain=".seewo.com",
        path="/",
        httponly=True,
    )
    logger.info(
        "账户被登录: usrid({}) : 账户信息({}, {}, {})",
        userid,
        str(token_info.nick_name or ""),
        str(token_info.real_name or ""),
        str(token_info.join_unit_time),
    )
    background_tasks.add_task(
        _update_user_profile,
        services,
        record.user_id,
        token,
        nickname=str(token_info.nick_name or ""),
        avatar_url=str(token_info.avatar_url or ""),
    )
    return ok_response()


@router.get("/getData/SSOLOGOUT", response_model=OkResponse)
async def sso_logout(pt_type: str | None = None):
    return ok_response()


@router.delete("/deleteData", response_model=OkResponse)
async def delete_data():
    return ok_response()


@router.post("/savedata", response_model=OkResponse)
async def save_user_data(
    body: SaveBody,
    background_tasks: BackgroundTasks,
    services: Services = Depends(_get_services),
    db: AsyncSession = Depends(get_db),
):
    try:
        if isinstance(body, SaveUserBody):
            prev = await find_user(db, body.userid)
            key_uid = prev.user_id if prev else body.userid
            record = UserRecord(
                user_id=key_uid,
                active=prev.active if prev else True,
                phone=body.userid,
                password=body.password,
                nick_name=body.user_name,
                real_name=(prev.real_name if prev else ""),
                avatar_url=body.avatar_url,
                pt_timestamp=(prev.pt_timestamp if prev else None),
            )
            await save_user(db, record)
            if services.encryptor is None:
                raise HTTPException(status_code=503, detail="credential_encryption_unavailable")  # noqa: TRY301
            await save_credentials(db, key_uid, body.userid, body.password, services.encryptor)
            await db.commit()
            logger.info("更新用户信息: phone={} user_id={}", body.userid, key_uid)
            return ok_response()

        uid = body.pt_userid
        rec = await get_user(db, uid)
        if rec and rec.pt_timestamp is not None and rec.pt_timestamp > body.pt_timestamp:
            return ok_response()
        new_name = body.pt_nickname or (rec.nick_name if rec else "")
        new_img = body.pt_photourl or (rec.avatar_url if rec else "")
        real_name = rec.real_name if rec else ""
        candidate_token = str(body.pt_token or "")
        if candidate_token and (not candidate_token.endswith(TOKEN_OFFLINE_SUFFIX)):
            fetched_once = await fetch_user_info(services, candidate_token)
            real_name = fetched_once.get("realName") or real_name
        record = UserRecord(
            user_id=uid,
            active=rec.active if rec else False,
            phone=(body.pt_username or (rec.phone if rec else "")),
            password=(rec.password if rec else ""),
            nick_name=new_name or "",
            real_name=real_name or (rec.real_name if rec else ""),
            avatar_url=new_img or "",
            pt_timestamp=body.pt_timestamp,
        )
        await save_user(db, record)
        if services.encryptor is None:
            raise HTTPException(status_code=503, detail="credential_encryption_unavailable")  # noqa: TRY301
        if rec is None and not body.pt_username:
            raise HTTPException(status_code=400, detail="credential_account_required")  # noqa: TRY301
        if rec is None and not body.pt_token:
            raise HTTPException(status_code=400, detail="credential_password_required")  # noqa: TRY301
        await db.commit()

        if body.pt_token and not body.pt_token.endswith(TOKEN_OFFLINE_SUFFIX):
            background_tasks.add_task(
                _update_user_profile,
                services,
                uid,
                body.pt_token,
                nickname=body.pt_nickname,
                avatar_url=body.pt_photourl,
            )

        return ok_response()
    except Exception:
        await db.rollback()
        raise


@router.post("/saveData", response_model=OkResponse)
async def save_data_alias(
    body: SaveBody,
    background_tasks: BackgroundTasks,
    services: Services = Depends(_get_services),
    db: AsyncSession = Depends(get_db),
):
    return await save_user_data(body, background_tasks, services, db)
