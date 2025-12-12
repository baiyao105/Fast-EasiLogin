import json

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from loguru import logger

from api.user_auth.auth_service import (
    is_token_invalid,
    user_login,
)
from api.user_auth.user_service import (
    fetch_user_info_with_token,
    get_aggregated_user_info,
)
from shared.constants import TOKEN_MASK_MIN_LEN
from shared.models import AppSaveDataBody, SaveUserBody, UserInfoRequest, UserRecord
from shared.storage import (
    get_cache,
    invalidate_token_cache,
    load_users,
    save_users_async,
)

from .state import (
    _INFLIGHT_LOCK,
    _INFLIGHT_USERS,
    TOKEN_TTL,
    clear_inflight,
    try_mark_inflight,
    ttl_with_jitter,
)

router = APIRouter()


@logger.catch
@router.get("/savedata")
async def savedata():
    return {"message": "success", "statusCode": "200"}


@logger.catch
@router.post("/user/info")
async def user_info(body: UserInfoRequest):
    data = await get_aggregated_user_info(body.user_id, body.password, body.fields)
    return {"message": "success", "statusCode": "200", "data": data}


@logger.catch
@router.get("/getData/SSOLOGIN")
async def get_sso_list(pt_type: str | None = None):
    users = load_users()
    data: list[dict[str, str]] = [
        {
            "pt_nickname": u.user_nickname,
            "pt_appid": u.userid,
            "pt_userid": (u.user_id or u.userid),
            "pt_username": u.user_realname or u.userid,
            "pt_photourl": u.head_img,
        }
        for u in users.values()
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
    r = get_cache()

    def _mask(t: str) -> str:
        if not t:
            return ""
        return f"{t[:6]}...{t[-4:]}" if len(t) > TOKEN_MASK_MIN_LEN else t

    token_bytes = await r.get(f"token_by_user:{userid}")
    if token_bytes:
        token = token_bytes.decode("utf-8")
        invalid = False
        try:
            if await try_mark_inflight(token):
                invalid = await is_token_invalid(token, fast=True)
        finally:
            await clear_inflight(token)
        if not invalid:
            response.headers["Set-Cookie"] = f"pt_token={token};Domain=.seewo.com; Path=/; HttpOnly"
            raw = await r.get(f"token_index:{token}")
            if raw:
                try:
                    idx = json.loads(raw)
                except Exception:
                    idx = {}
                uid = idx.get("uid")
                await r.set(f"token_by_user:{userid}", token, ex=ttl_with_jitter(TOKEN_TTL))
                if uid:
                    await r.set(f"token_by_uid:{uid!s}", token, ex=ttl_with_jitter(TOKEN_TTL))
                await r.set(
                    f"token_index:{token}",
                    raw.decode("utf-8") if isinstance(raw, bytes) else raw,
                    ex=ttl_with_jitter(TOKEN_TTL),
                )
            return {"message": "success", "statusCode": "200"}
        await invalidate_token_cache(token)
    users = load_users()
    record = users.get(userid)
    if not record:
        raise HTTPException(status_code=404, detail={"message": "user_not_found", "statusCode": "404"})
    try:
        token_info = await user_login(userid, record.password)
    except HTTPException as e:
        if e.status_code == 504:  # noqa: PLR2004
            logger.error("网络错误: 获取新token失败: userid={}", userid)
        elif e.status_code == 401:  # noqa: PLR2004
            logger.warning("登录失败: 账号或密码错误: userid={}", userid)
        raise
    token = str(token_info.get("token") or "")
    response.headers["Set-Cookie"] = f"pt_token={token};Domain=.seewo.com; Path=/; HttpOnly"
    await r.set(f"token_by_user:{userid}", token, ex=ttl_with_jitter(TOKEN_TTL))
    uid = token_info.get("uid")
    if uid:
        await r.set(f"token_by_uid:{uid!s}", token, ex=ttl_with_jitter(TOKEN_TTL))
    idx = {"userid": userid, "uid": uid}
    await r.set(f"token_index:{token}", json.dumps(idx, ensure_ascii=False), ex=ttl_with_jitter(TOKEN_TTL))
    logger.info(
        "账户被登录: usrid({}) : 账户信息({}, {}, {})",
        userid,
        str(token_info.get("nickName") or ""),
        str(token_info.get("realName") or ""),
        str(token_info.get("joinUnitTime")),
    )
    logger.trace("登录信息: uid={} token={}", uid, _mask(token))

    @logger.catch
    async def _validate_token_after_login(tok: str):
        try:
            if not await try_mark_inflight(tok):
                return
            if await is_token_invalid(tok):
                await invalidate_token_cache(tok)
                logger.warning("token invalid after login: token={}", _mask(tok))
        except Exception:
            pass
        finally:
            await clear_inflight(tok)

    background_tasks.add_task(_validate_token_after_login, token)

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
            real_name = fetched.get("realName") or rec.user_realname or uid
            changed = (
                (new_name or "") != (rec.user_nickname or "")
                or (real_name or "") != (rec.user_realname or uid)
                or (new_img or "") != (rec.head_img or "")
            )
            users_local[uid] = UserRecord(
                userid=uid,
                password=rec.password,
                user_nickname=new_name or "",
                user_realname=real_name or uid,
                head_img=new_img or "",
                pt_timestamp=rec.pt_timestamp,
            )
            await save_users_async(users_local, expected_mtime=None)
            if changed:
                logger.success(
                    "账户信息被更新: usrid({}) {}",
                    uid,
                    str({"nickName": new_name, "realName": real_name, "head_img": new_img}),
                )
        finally:
            async with _INFLIGHT_LOCK:
                _INFLIGHT_USERS.discard(uid)

    background_tasks.add_task(_update_user_profile, userid, token_info)

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
        prev = users.get(body.userid)
        users[body.userid] = UserRecord(
            userid=body.userid,
            password=body.password,
            user_nickname=body.user_name,
            user_realname=(prev.user_realname if prev else body.userid),
            head_img=body.head_img,
            pt_timestamp=(prev.pt_timestamp if prev else None),
            user_id=(prev.user_id if prev else None),
        )
        await save_users_async(users, expected_mtime=None)
        logger.info("update account info: userid={}", body.userid)
        return {"message": "success", "statusCode": "200"}
    uid = body.pt_userid
    uname = body.pt_username
    rec = users.get(uname) or users.get(uid)
    if rec and rec.pt_timestamp is not None and rec.pt_timestamp >= body.pt_timestamp:
        return {"message": "success", "statusCode": "200"}
    new_name = body.pt_nickname or (rec.user_nickname if rec else "")
    new_img = body.pt_photourl or (rec.head_img if rec else "")
    real_name = rec.user_realname if rec else uname
    candidate_token = str(body.pt_token or "")
    if (
        candidate_token
        and (not candidate_token.endswith("-offline"))
        and (not await is_token_invalid(candidate_token, fast=True))
    ):
        fetched_once = await fetch_user_info_with_token(candidate_token)
        real_name = fetched_once.get("realName") or real_name
    key = uname
    users[key] = UserRecord(
        userid=key,
        password=(rec.password if rec else ""),
        user_nickname=new_name or "",
        user_realname=real_name or uname,
        head_img=new_img or "",
        pt_timestamp=body.pt_timestamp,
        user_id=uid,
    )
    await save_users_async(users, expected_mtime=None)

    if body.pt_token:

        @logger.catch
        async def _update_user_profile(uid_local: str, uname_local: str, token_local: str):
            key_local = uname_local or uid_local
            async with _INFLIGHT_LOCK:
                if key_local in _INFLIGHT_USERS:
                    return
                _INFLIGHT_USERS.add(key_local)
            try:
                users_local = load_users()
                rec_local = users_local.get(uname_local) or users_local.get(uid_local)
                if not rec_local:
                    return
                fetched = await fetch_user_info_with_token(token_local)
                new_name_local = fetched.get("nickName") or rec_local.user_nickname
                new_img_local = fetched.get("PhotoUrl") if False else fetched.get("photoUrl") or rec_local.head_img
                real_name_local = fetched.get("realName") or rec_local.user_realname or uname_local
                changed_local = (
                    (new_name_local or "") != (rec_local.user_nickname or "")
                    or (real_name_local or "") != (rec_local.user_realname or uname_local)
                    or (new_img_local or "") != (rec_local.head_img or "")
                )
                users_local[uname_local] = UserRecord(
                    userid=uname_local,
                    password=rec_local.password,
                    user_nickname=new_name_local or "",
                    user_realname=real_name_local or uname_local,
                    head_img=new_img_local or "",
                    pt_timestamp=rec_local.pt_timestamp,
                    user_id=uid_local,
                )
                await save_users_async(users_local, expected_mtime=None)
                if changed_local:
                    logger.success(
                        "账户信息被更新: usrid({}) {}",
                        uname_local,
                        str({"nickName": new_name_local, "realName": real_name_local, "head_img": new_img_local}),
                    )
            finally:
                async with _INFLIGHT_LOCK:
                    _INFLIGHT_USERS.discard(key_local)

        candidate = str(body.pt_token)
        if (not candidate.endswith("-offline")) and (not await is_token_invalid(candidate)):
            background_tasks.add_task(_update_user_profile, uid, uname, candidate)

    return {"message": "success", "statusCode": "200"}


@logger.catch
@router.post("/saveData")
async def save_data(body: SaveUserBody | AppSaveDataBody, background_tasks: BackgroundTasks):
    return await save_user(body, background_tasks)
