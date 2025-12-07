# import contextlib
import asyncio
import contextlib
import json
import random
import time
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse

from shared.models import AppSaveDataBody, SaveUserBody, UserInfoRequest, UserRecord
from shared.storage import (
    cache_count,
    cache_iter_prefix,
    clear_cache,
    close_cache,
    get_cache,
    load_appsettings,
    load_users,
    save_users_async,
)

from .core.user_manger import (
    close_http_client,
    fetch_user_info_with_token,
    get_aggregated_user_info,
    init_http_client,
    is_token_invalid,
    user_login,
)

app = FastAPI(default_response_class=ORJSONResponse)
_REQ_BUCKETS: list[int] = [0] * 1440
_REQ_LAST_MINUTE: int | None = None
_LOGS: list[dict[str, str]] = []
_INFLIGHT_USERS: set[str] = set()
_INFLIGHT_LOCK = asyncio.Lock()

TOKEN_TTL = 600.0


def _ttl(base: float) -> int:
    j = random.uniform(0.8, 1.2)
    return max(5, int(base * j))


@app.middleware("http")
async def add_global_headers(request, call_next):
    now = time.time()
    minute = int(now // 60)
    idx = minute % 1440
    global _REQ_LAST_MINUTE
    if _REQ_LAST_MINUTE is None:
        _REQ_LAST_MINUTE = minute
    if minute != _REQ_LAST_MINUTE:
        if (minute - _REQ_LAST_MINUTE) >= 1440:
            _REQ_BUCKETS[:] = [0] * 1440
        else:
            for m in range(_REQ_LAST_MINUTE + 1, minute + 1):
                _REQ_BUCKETS[m % 1440] = 0
        _REQ_LAST_MINUTE = minute
    _REQ_BUCKETS[idx] += 1
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,DELETE"
    response.headers["Content-Type"] = "application/json; charset=UTF-8"
    return response


app.add_middleware(GZipMiddleware, minimum_size=500)


@app.on_event("startup")
async def _startup():
    await init_http_client()
    await clear_cache()
    _LOGS.append({"time": time.strftime("%H:%M:%S", time.localtime()), "level": "INFO", "text": "service started"})
    with contextlib.suppress(Exception):
        app.state.token_renew = asyncio.create_task(_token_renew_job())


@app.on_event("shutdown")
async def _shutdown():
    await close_http_client()
    await clear_cache()
    await close_cache()
    try:
        t = getattr(app.state, "token_renew", None)
        if t:
            t.cancel()
    except Exception:
        pass


@app.get("/savedata")
async def savedata():
    return {"message": "success", "statusCode": "200"}


@app.post("/user/info")
async def user_info(body: UserInfoRequest):
    data = await get_aggregated_user_info(body.user_id, body.password, body.fields)
    return {"message": "success", "statusCode": "200", "data": data}


@app.get("/getData/SSOLOGIN")
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


@app.get("/getData/SSOLOGIN/{userid}")
async def sso_login_user(
    userid: str,
    response: Response,
    background_tasks: BackgroundTasks,
    pt_type: str | None = None,
    pt_appid: str | None = None,
):
    r = get_cache()
    token_bytes = await r.get(f"token_by_user:{userid}")
    now = time.time()
    if token_bytes:
        token = token_bytes.decode("utf-8")
        response.headers["Set-Cookie"] = f"pt_token={token};Domain=.seewo.com; Path=/; HttpOnly"

        async def _validate_token_and_invalidate(tok: str):
            try:
                if await is_token_invalid(tok):
                    idx_raw = await r.get(f"token_index:{tok}")
                    if idx_raw:
                        try:
                            idx = json.loads(idx_raw)
                        except Exception:
                            idx = {}
                        uid = idx.get("uid")
                        uid_key = f"token_by_uid:{uid}" if uid else None
                        await r.delete(f"token_by_user:{idx.get('userid')}")
                        if uid_key:
                            await r.delete(uid_key)
                    await r.delete(f"token_index:{tok}")
            except Exception:
                pass

        background_tasks.add_task(_validate_token_and_invalidate, token)
        return {"message": "success", "statusCode": "200"}
    users = load_users()
    record = users.get(userid)
    if not record:
        raise HTTPException(status_code=404, detail={"message": "user_not_found", "statusCode": "404"})
    token_info = await user_login(userid, record.password)
    token = str(token_info.get("token") or "")
    response.headers["Set-Cookie"] = f"pt_token={token};Domain=.seewo.com; Path=/; HttpOnly"
    await r.set(f"token_by_user:{userid}", token, ex=_ttl(TOKEN_TTL))
    uid = token_info.get("uid")
    if uid:
        await r.set(f"token_by_uid:{uid!s}", token, ex=_ttl(TOKEN_TTL))
    idx = {"userid": userid, "uid": uid}
    await r.set(f"token_index:{token}", json.dumps(idx, ensure_ascii=False), ex=_ttl(TOKEN_TTL))

    async def _validate_token_after_login(tok: str):
        try:
            if await is_token_invalid(tok):
                await _invalidate_token_cache(tok)
        except Exception:
            pass

    background_tasks.add_task(_validate_token_after_login, token)

    async def _update_user_profile(uid: str, info: dict[str, Any]):
        async with _INFLIGHT_LOCK:
            if uid in _INFLIGHT_USERS:
                return
            _INFLIGHT_USERS.add(uid)
        try:
            users_local = load_users()
            rec = users_local.get(uid)
            if not rec:
                return
            fetched = await fetch_user_info_with_token(info.get("token") or "")
            new_name = fetched.get("nickName") or info.get("user_name") or rec.user_nickname
            new_img = fetched.get("photoUrl") or info.get("head_img") or rec.head_img
            real_name = fetched.get("realName") or rec.user_realname or uid
            users_local[uid] = UserRecord(
                userid=uid,
                password=rec.password,
                user_nickname=new_name or "",
                user_realname=real_name or uid,
                head_img=new_img or "",
                pt_timestamp=rec.pt_timestamp,
            )
            await save_users_async(users_local, expected_mtime=None)
        finally:
            async with _INFLIGHT_LOCK:
                _INFLIGHT_USERS.discard(uid)

    background_tasks.add_task(_update_user_profile, userid, token_info)
    _LOGS.append(
        {
            "time": time.strftime("%H:%M:%S", time.localtime()),
            "level": "INFO",
            "text": f"login success /user/agg/{userid}",
        }
    )
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


async def _invalidate_token_cache(token: str) -> None:
    r = get_cache()
    raw = await r.get(f"token_index:{token}")
    userid = None
    if raw:
        try:
            idx = json.loads(raw)
        except Exception:
            idx = {}
        await r.delete(f"token_by_user:{idx.get('userid')}")
        uid = idx.get("uid")
        if uid:
            await r.delete(f"token_by_uid:{uid}")
        try:
            userid = idx.get("userid")
        except Exception:
            userid = None
    await r.delete(f"token_index:{token}")
    if userid:
        keys_login = await cache_iter_prefix(f"login:{userid}:")
        for k in keys_login:
            with contextlib.suppress(Exception):
                await r.delete(k)
        keys_agg = await cache_iter_prefix(f"agg:{userid}:")
        for k in keys_agg:
            with contextlib.suppress(Exception):
                await r.delete(k)


@app.get("/getData/SSOLOGOUT")
async def sso_logout(request: Request, response: Response, pt_type: str | None = None):
    # if request is None:
    #     return {"message": "success", "statusCode": "200"}
    # 本来是直接失效的,但是发现还能用.
    # token = _extract_pt_token(request)
    # if token:
    #     _invalidate_token(token)
    #     if response is not None:
    #         with contextlib.suppress(Exception):
    #             response.delete_cookie("pt_token", domain=".seewo.com", path="/")
    return {"message": "success", "statusCode": "200"}


@app.delete("/deleteData")
async def delete_data(request: Request, response: Response):
    # 本来是直接失效的,但是发现还能用.
    # token = _extract_pt_token(request)
    # if token:
    #     _invalidate_token(token)
    #     with contextlib.suppress(Exception):
    #         response.delete_cookie("pt_token", domain=".seewo.com", path="/")
    return {"message": "success", "statusCode": "200"}


@app.post("/savedata")
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
        _LOGS.append(
            {"time": time.strftime("%H:%M:%S", time.localtime()), "level": "INFO", "text": f"add user {body.userid}"}
        )
        return {"message": "success", "statusCode": "200"}
    uid = body.pt_userid
    uname = body.pt_username
    # entry = TOKEN_CACHE.get(uid) or TOKEN_CACHE.get(uname)
    # now = time.time()
    # if body.pt_token:
    #     candidate = str(body.pt_token)
    #     if (
    #         (not candidate.endswith("-offline"))
    #         and (not await is_token_invalid(candidate))
    #         and (not entry or entry.get("token") != candidate)
    #     ):
    #         TOKEN_CACHE[uid] = {"token": candidate, "exp": now + TOKEN_TTL}
    #         TOKEN_CACHE[uname] = {"token": candidate, "exp": now + TOKEN_TTL}
    rec = users.get(uname) or users.get(uid)
    if rec and rec.pt_timestamp is not None and rec.pt_timestamp >= body.pt_timestamp:
        return {"message": "success", "statusCode": "200"}
    new_name = body.pt_nickname or (rec.user_nickname if rec else "")
    new_img = body.pt_photourl or (rec.head_img if rec else "")
    real_name = rec.user_realname if rec else uname
    candidate_token = str(body.pt_token or "")
    if candidate_token and (not candidate_token.endswith("-offline")) and (not await is_token_invalid(candidate_token)):
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
                new_img_local = fetched.get("photoUrl") or rec_local.head_img
                real_name_local = fetched.get("realName") or rec_local.user_realname or uname_local
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
            finally:
                async with _INFLIGHT_LOCK:
                    _INFLIGHT_USERS.discard(key_local)

        candidate = str(body.pt_token)
        if (not candidate.endswith("-offline")) and (not await is_token_invalid(candidate)):
            background_tasks.add_task(_update_user_profile, uid, uname, candidate)
    _LOGS.append({"time": time.strftime("%H:%M:%S", time.localtime()), "level": "INFO", "text": f"save user {uname}"})
    return {"message": "success", "statusCode": "200"}


@app.post("/saveData")
async def save_data(body: SaveUserBody | AppSaveDataBody, background_tasks: BackgroundTasks):
    return await save_user(body, background_tasks)


@app.get("/metrics")
async def metrics():
    settings = load_appsettings()
    users = load_users()
    accounts_total = len(users)
    cached_logins = await cache_count("login:")
    active_tokens = await cache_count("token_by_user:")
    now = time.time()
    minute = int(now // 60)
    idx = minute % 1440
    b = _REQ_BUCKETS
    requests_24h = sum(b)
    requests_5m = 0
    for i in range(5):
        requests_5m += b[(idx - i) % 1440]
    data = {
        "service": {
            "running": True,
            "address": "127.0.0.1",
            "port": int(settings.get("port", 24300)),
        },
        "accounts_total": accounts_total,
        "cached_logins": cached_logins,
        "requests_24h": requests_24h,
        "active_tokens": active_tokens,
        "invalid_tokens": 0,
        "requests_5m": requests_5m,
        "updated_at": time.strftime("%H:%M:%S", time.localtime()),
        "logs": _LOGS[-20:],
    }
    return {"message": "success", "statusCode": "200", "data": data}


async def _token_renew_job():
    r = get_cache()
    while True:
        try:
            tokens = await cache_iter_prefix("token_index:")
            for k in tokens:
                try:
                    tok = k.split(":", 1)[1]
                except Exception:
                    tok = ""
                if not tok:
                    continue
                try:
                    if not await is_token_invalid(tok):
                        raw = await r.get(f"token_index:{tok}")
                        if raw:
                            try:
                                idx = json.loads(raw)
                            except Exception:
                                idx = {}
                            userid = idx.get("userid")
                            uid = idx.get("uid")
                            if userid:
                                await r.set(f"token_by_user:{userid}", tok, ex=_ttl(TOKEN_TTL))
                            if uid:
                                await r.set(f"token_by_uid:{uid}", tok, ex=_ttl(TOKEN_TTL))
                            await r.set(
                                f"token_index:{tok}",
                                raw.decode("utf-8") if isinstance(raw, bytes) else raw,
                                ex=_ttl(TOKEN_TTL),
                            )
                    else:
                        await _invalidate_token_cache(tok)
                except Exception:
                    pass
        except Exception:
            pass
        await asyncio.sleep(30)
