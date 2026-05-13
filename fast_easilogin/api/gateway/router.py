from fastapi import APIRouter, BackgroundTasks, HTTPException, Response
from loguru import logger

from fast_easilogin.api.user_auth.auth_service import user_login
from fast_easilogin.api.user_auth.user_service import fetch_user_info_with_token, get_aggregated_user_info
from fast_easilogin.shared.constants import TOKEN_OFFLINE_SUFFIX
from fast_easilogin.shared.store.config import find_user, load_users, save_users_async
from fast_easilogin.shared.store.models import AppSaveDataBody, SaveUserBody, UserInfoRequest, UserRecord

from .state import _INFLIGHT_LOCK, _INFLIGHT_USERS

router = APIRouter()


async def _update_user_profile(uid: str, token: str, nickname: str | None = None, head_img: str | None = None) -> None:
    async with _INFLIGHT_LOCK:
        if uid in _INFLIGHT_USERS:
            return
        _INFLIGHT_USERS.add(uid)
    try:
        users = load_users()
        rec = users.get(uid)
        if not rec:
            return
        fetched = await fetch_user_info_with_token(token)
        if not fetched:
            return
        new_name = fetched.get("nickName") or nickname or rec.user_nickname
        new_img = fetched.get("photoUrl") or head_img or rec.head_img
        real_name = fetched.get("realName") or rec.user_realname or ""
        changed = (
            (new_name or "") != (rec.user_nickname or "")
            or (real_name or "") != (rec.user_realname or "")
            or (new_img or "") != (rec.head_img or "")
        )
        if not changed:
            return
        users[uid] = UserRecord(
            user_id=uid,
            active=rec.active,
            phone=rec.phone,
            password=rec.password,
            user_nickname=new_name or "",
            user_realname=real_name,
            head_img=new_img or "",
            pt_timestamp=rec.pt_timestamp,
        )
        await save_users_async(users, user_ids=[uid])
        logger.success(
            "账户信息被更新: usrid({}) {}", uid, {"nickName": new_name, "realName": real_name, "head_img": new_img}
        )
    finally:
        async with _INFLIGHT_LOCK:
            _INFLIGHT_USERS.discard(uid)


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
    logger.info(
        "账户被登录: usrid({}) : 账户信息({}, {}, {})",
        userid,
        str(token_info.get("nickName") or ""),
        str(token_info.get("realName") or ""),
        str(token_info.get("joinUnitTime")),
    )
    background_tasks.add_task(
        _update_user_profile,
        record.user_id,
        token,
        nickname=str(token_info.get("nickName") or ""),
        head_img=str(token_info.get("head_img") or ""),
    )
    return {"message": "success", "statusCode": "200"}


@logger.catch
@router.get("/getData/SSOLOGOUT")
async def sso_logout(pt_type: str | None = None):
    return {"message": "success", "statusCode": "200"}


@logger.catch
@router.delete("/deleteData")
async def delete_data():
    return {"message": "success", "statusCode": "200"}


@logger.catch
@router.post("/savedata")
async def save_user(body: SaveUserBody | AppSaveDataBody, background_tasks: BackgroundTasks):
    users = load_users()
    if isinstance(body, SaveUserBody):
        key_uid = body.userid
        prev = users.get(body.userid) or next((r for r in users.values() if r.phone == body.userid), None)
        if prev:
            key_uid = prev.user_id
        active_val = prev.active if prev else True
        users[key_uid] = UserRecord(
            user_id=key_uid,
            active=active_val,
            phone=body.userid,
            password=body.password,
            user_nickname=body.user_name,
            user_realname=(prev.user_realname if prev else ""),
            head_img=body.head_img,
            pt_timestamp=(prev.pt_timestamp if prev else None),
        )
        await save_users_async(users, user_ids=[key_uid])
        logger.info("更新用户信息: phone={} user_id={}", body.userid, key_uid)
        return {"message": "success", "statusCode": "200"}
    uid = body.pt_userid
    rec = users.get(uid)
    if rec and rec.pt_timestamp is not None and rec.pt_timestamp > body.pt_timestamp:
        return {"message": "success", "statusCode": "200"}
    new_name = body.pt_nickname or (rec.user_nickname if rec else "")
    new_img = body.pt_photourl or (rec.head_img if rec else "")
    real_name = rec.user_realname if rec else ""
    candidate_token = str(body.pt_token or "")
    if candidate_token and (not candidate_token.endswith(TOKEN_OFFLINE_SUFFIX)):
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
    await save_users_async(users, user_ids=[key])

    if body.pt_token and not body.pt_token.endswith(TOKEN_OFFLINE_SUFFIX):
        background_tasks.add_task(
            _update_user_profile,
            uid,
            body.pt_token,
            nickname=body.pt_nickname,
            head_img=body.pt_photourl,
        )

    return {"message": "success", "statusCode": "200"}


@logger.catch
@router.post("/saveData")
async def save_data(body: SaveUserBody | AppSaveDataBody, background_tasks: BackgroundTasks):
    return await save_user(body, background_tasks)
