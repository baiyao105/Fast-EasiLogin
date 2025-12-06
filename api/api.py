# import contextlib
import time
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response

from shared.models import AppSaveDataBody, SaveUserBody, UserInfoRequest, UserRecord
from shared.storage import load_users, save_users

from .core.user_manger import fetch_user_info_with_token, get_aggregated_user_info, user_login

app = FastAPI()

TOKEN_CACHE: dict[str, dict[str, str | float]] = {}
TOKEN_TTL = 900.0


@app.middleware("http")
async def add_global_headers(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,DELETE"
    response.headers["Content-Type"] = "application/json; charset=UTF-8"
    return response


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
            "pt_userid": u.userid,
            "pt_username": u.user_realname or u.userid,
            "pt_photourl": u.head_img,
        }
        for u in users.values()
    ]
    return {"message": "success", "statusCode": "200", "data": data}


@app.get("/getData/SSOLOGIN/{userid}")
async def sso_login_user(
    userid: str,
    pt_type: str | None = None,
    pt_appid: str | None = None,
    response: Response = None,
    background_tasks: BackgroundTasks = None,
):
    entry = TOKEN_CACHE.get(userid)
    now = time.time()
    if entry and entry.get("exp", 0.0) > now:
        token = entry.get("token")  # type: ignore
        response.headers["Set-Cookie"] = f"pt_token={token};Domain=.seewo.com; Path=/; HttpOnly"
        return {"message": "success", "statusCode": "200"}
    users = load_users()
    record = users.get(userid)
    if not record:
        raise HTTPException(status_code=404, detail={"message": "user_not_found", "statusCode": "404"})
    token_info = await user_login(userid, record.password)
    token = token_info.get("token")
    response.headers["Set-Cookie"] = f"pt_token={token};Domain=.seewo.com; Path=/; HttpOnly"
    TOKEN_CACHE[userid] = {"token": token, "exp": now + TOKEN_TTL}

    async def _update_user_profile(uid: str, info: dict[str, Any]):
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
        save_users(users_local)

    background_tasks.add_task(_update_user_profile, userid, token_info)
    return {"message": "success", "statusCode": "200"}


def _extract_pt_token(request: Request) -> str | None:
    token = request.cookies.get("pt_token")
    if token:
        return token
    cookie_header = request.headers.get("Cookie") or ""
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith("pt_token="):
            return part.split("=", 1)[1]
    return None


def _invalidate_token(token: str) -> bool:
    removed = False
    for uid, entry in list(TOKEN_CACHE.items()):
        if entry.get("token") == token:
            del TOKEN_CACHE[uid]
            removed = True
    return removed


@app.get("/getData/SSOLOGOUT")
async def sso_logout(pt_type: str | None = None, request: Request = None, response: Response = None):
    if request is None:
        return {"message": "success", "statusCode": "200"}
    # token = _extract_pt_token(request)
    # if token:
    #     _invalidate_token(token)
    #     if response is not None:
    #         with contextlib.suppress(Exception):
    #             response.delete_cookie("pt_token", domain=".seewo.com", path="/")
    return {"message": "success", "statusCode": "200"}


@app.delete("/deleteData")
async def delete_data(request: Request, response: Response):
    # token = _extract_pt_token(request)
    # if token:
    #     _invalidate_token(token)
    #     with contextlib.suppress(Exception):
    #         response.delete_cookie("pt_token", domain=".seewo.com", path="/")
    return {"message": "success", "statusCode": "200"}


@app.post("/savedata")
async def save_user(body: SaveUserBody | AppSaveDataBody):
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
        )
        save_users(users)
        return {"message": "success", "statusCode": "200"}
    entry = TOKEN_CACHE.get(body.pt_username)
    if not entry or entry.get("token") != body.pt_token:
        return {"message": "token_mismatch", "statusCode": "400"}
    rec = users.get(body.pt_username)
    if rec and rec.pt_timestamp is not None and rec.pt_timestamp >= body.pt_timestamp:
        return {"message": "success", "statusCode": "200"}
    new_name = body.pt_nickname or (rec.user_nickname if rec else "")
    new_img = body.pt_photourl or (rec.head_img if rec else "")
    users[body.pt_username] = UserRecord(
        userid=body.pt_username,
        password=(rec.password if rec else ""),
        user_nickname=new_name or "",
        user_realname=body.pt_username,
        head_img=new_img or "",
        pt_timestamp=body.pt_timestamp,
    )
    save_users(users)
    return {"message": "success", "statusCode": "200"}


@app.post("/saveData")
async def save_data(body: SaveUserBody | AppSaveDataBody):
    return await save_user(body)
