from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from loguru import logger

from fast_easilogin.api.user_auth.auth_service import (
    user_login,
)
from fast_easilogin.api.user_auth.user_service import (
    fetch_user_info_with_token,
    get_aggregated_user_info,
)
from fast_easilogin.shared.constants import TOKEN_MASK_MIN_LEN
from fast_easilogin.shared.store.config import (
    find_user,
    load_users,
    save_users_async,
)
from fast_easilogin.shared.store.models import AppSaveDataBody, SaveUserBody, UserInfoRequest, UserRecord

from .state import (
    _INFLIGHT_LOCK,
    _INFLIGHT_USERS,
)

router = APIRouter()


@logger.catch
@router.get("/savedata")
async def savedata():
    return {"message": "success", "statusCode": "200"}


@logger.catch
@router.post("/user/info")
async def user_info(body: UserInfoRequest):
    logger.info("聚合用户信息: user_id={} fields_count={}", body.user_id, len(body.fields or []))
    data = await get_aggregated_user_info(body.user_id, body.password, body.fields)
    return {"message": "success", "statusCode": "200", "data": data}


@logger.catch
@router.get("/getData/SSOLOGIN")
async def get_sso_list(pt_type: str | None = None):
    users = load_users()
    data: list[dict[str, str]] = [
        {
            "pt_nickname": u.user_nickname,
            "pt_appid": u.user_id,
            "pt_userid": u.user_id,
            "pt_username": u.user_realname or u.user_id,
            "pt_photourl": u.head_img,
        }
        for u in users.values()
        if u.active
    ]
    # logger.info("SSO列表: count={}", len(data))
    return {"message": "success", "statusCode": "200", "data": data}


@logger.catch
@router.get("/getData/SSOLOGIN/{userid}")
async def sso_login_user(
    userid: str,
    response: Response,
    background_tasks: BackgroundTasks,
    pt_type: str | None = None,
    pt_appid: str | None = None,
):
    def _mask(t: str) -> str:
        if not t:
            return ""
        return f"{t[:6]}...{t[-4:]}" if len(t) > TOKEN_MASK_MIN_LEN else t

    users = load_users()
    record = find_user(userid, users)
    if record is None or not record.active:
        raise HTTPException(status_code=404, detail={"message": "user_not_found", "statusCode": "404"})
    login_account = record.phone or userid
    token_info = await user_login(login_account, record.password, _userid=record.user_id)
    token = str(token_info.get("token") or "")
    response.set_cookie(
        key="pt_token",
        value=token,
        domain=".seewo.com",
        path="/",
        httponly=True,
    )
    uid = token_info.get("uid")
    logger.info(
        "账户被登录: usrid({}) : 账户信息({}, {}, {})",
        userid,
        str(token_info.get("nickName") or ""),
        str(token_info.get("realName") or ""),
        str(token_info.get("joinUnitTime")),
    )
    logger.trace("登录信息: uid={} token={}", uid, _mask(token))

    @logger.catch
    async def _update_user_profile(uid: str, info: dict[str, str | dict]):
        async with _INFLIGHT_LOCK:
            if uid in _INFLIGHT_USERS:
                return
            _INFLIGHT_USERS.add(uid)
        try:
            users_local = load_users()
            rec = users_local.get(uid)
            if not rec:
                return
            fetched = await fetch_user_info_with_token(str(info.get("token") or ""))
            new_name = fetched.get("nickName") or str(info.get("user_name") or rec.user_nickname)
            new_img = fetched.get("photoUrl") or str(info.get("head_img") or rec.head_img)
            real_name = fetched.get("realName") or rec.user_realname or ""
            changed = (
                (new_name or "") != (rec.user_nickname or "")
                or (real_name or "") != (rec.user_realname or "")
                or (new_img or "") != (rec.head_img or "")
            )
            users_local[uid] = UserRecord(
                user_id=uid,
                active=rec.active,
                phone=rec.phone,
                password=rec.password,
                user_nickname=new_name or "",
                user_realname=(real_name or rec.user_realname or ""),
                head_img=new_img or "",
                pt_timestamp=rec.pt_timestamp,
            )
            await save_users_async(users_local, expected_mtime=None)
        finally:
            async with _INFLIGHT_LOCK:
                _INFLIGHT_USERS.discard(uid)

    background_tasks.add_task(_update_user_profile, record.user_id, token_info)

    return {"message": "success", "statusCode": "200"}


def _extract_pt_token(request: Request) -> str | None:
    token = request.cookies.get("pt_token")
    if token:
        return token
    cookie_header = request.headers.get("Cookie") or ""
    for part in cookie_header.split(";"):
        p = part.strip()
        if p.startswith("pt_token="):
            return p.split("=", 1)[1]
    return None


@logger.catch
@router.get("/getData/SSOLOGOUT")
async def sso_logout(request: Request, response: Response, pt_type: str | None = None):
    return {"message": "success", "statusCode": "200"}


@logger.catch
@router.delete("/deleteData")
async def delete_data(request: Request, response: Response):
    return {"message": "success", "statusCode": "200"}


@logger.catch
@router.post("/savedata")
async def save_user(body: SaveUserBody | AppSaveDataBody, background_tasks: BackgroundTasks):
    users = load_users()
    if isinstance(body, SaveUserBody):
        prev = next((r for r in users.values() if r.phone == body.userid), None)
        key_uid = prev.user_id if prev else None
        active_val = prev.active if prev else False
        users[key_uid or body.userid] = UserRecord(
            user_id=(key_uid or body.userid),
            active=active_val,
            phone=body.userid,
            password=body.password,
            user_nickname=body.user_name,
            user_realname=(prev.user_realname if prev else ""),
            head_img=body.head_img,
            pt_timestamp=(prev.pt_timestamp if prev else None),
        )
        await save_users_async(users, expected_mtime=None)
        logger.info("更新用户信息: phone={} user_id={}", body.userid, key_uid or "-")
        return {"message": "success", "statusCode": "200"}
    uid = body.pt_userid
    uname = body.pt_username
    rec = users.get(uid)
    if rec and rec.pt_timestamp is not None and rec.pt_timestamp >= body.pt_timestamp:
        return {"message": "success", "statusCode": "200"}
    new_name = body.pt_nickname or (rec.user_nickname if rec else "")
    new_img = body.pt_photourl or (rec.head_img if rec else "")
    real_name = rec.user_realname if rec else ""
    candidate_token = str(body.pt_token or "")
    if candidate_token and (not candidate_token.endswith("-offline")):
        fetched_once = await fetch_user_info_with_token(candidate_token)
        real_name = fetched_once.get("realName") or real_name
    key = uid
    active_val = rec.active if rec else False
    users[key] = UserRecord(
        user_id=key,
        active=active_val,
        phone=(body.pt_username or (rec.phone if rec else "")),
        password=(rec.password if rec else ""),
        user_nickname=new_name or "",
        user_realname=real_name or (rec.user_realname if rec else ""),
        head_img=new_img or "",
        pt_timestamp=body.pt_timestamp,
    )
    await save_users_async(users, expected_mtime=None)

    if body.pt_token:

        @logger.catch
        async def _update_user_profile(uid_local: str, uname_local: str, token_local: str):
            key_local = uid_local
            async with _INFLIGHT_LOCK:
                if key_local in _INFLIGHT_USERS:
                    return
                _INFLIGHT_USERS.add(key_local)
            try:
                users_local = load_users()
                rec_local = users_local.get(uid_local)
                if not rec_local:
                    return
                fetched = await fetch_user_info_with_token(token_local)
                new_name_local = fetched.get("nickName") or rec_local.user_nickname
                new_img_local = fetched.get("PhotoUrl") if False else fetched.get("photoUrl") or rec_local.head_img
                real_name_local = fetched.get("realName") or rec_local.user_realname or ""
                changed_local = (
                    (new_name_local or "") != (rec_local.user_nickname or "")
                    or (real_name_local or "") != (rec_local.user_realname or "")
                    or (new_img_local or "") != (rec_local.head_img or "")
                )
                users_local[key_local] = UserRecord(
                    user_id=key_local,
                    active=rec_local.active,
                    phone=rec_local.phone,
                    password=rec_local.password,
                    user_nickname=new_name_local or "",
                    user_realname=(real_name_local or rec_local.user_realname or ""),
                    head_img=new_img_local or "",
                    pt_timestamp=rec_local.pt_timestamp,
                )
                await save_users_async(users_local, expected_mtime=None)
                if changed_local:
                    logger.success(
                        "账户信息被更新: usrid({}) {}",
                        key_local,
                        str({"nickName": new_name_local, "realName": real_name_local, "head_img": new_img_local}),
                    )
            finally:
                async with _INFLIGHT_LOCK:
                    _INFLIGHT_USERS.discard(key_local)

        candidate = str(body.pt_token)
        if not candidate.endswith("-offline"):
            background_tasks.add_task(_update_user_profile, uid, uname, candidate)

    return {"message": "success", "statusCode": "200"}


@logger.catch
@router.post("/saveData")
async def save_data(body: SaveUserBody | AppSaveDataBody, background_tasks: BackgroundTasks):
    return await save_user(body, background_tasks)
