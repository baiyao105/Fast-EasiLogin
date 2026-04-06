import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from loguru import logger

from fast_easilogin.shared.store.config import (
    clear_cache,
    load_appsettings,
    load_users,
    save_users,
    save_users_async,
    write_config,
)
from fast_easilogin.shared.store.models import UserRecord
from fast_easilogin.webui import STATIC_DIR

router = APIRouter(tags=["webui"])


@router.get("/", response_class=HTMLResponse)
async def webui_index():
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="WebUI not found")
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))


@router.get("/users")
async def get_users():
    users = load_users()
    data = [
        {
            "user_id": u.user_id,
            "active": u.active,
            "phone": u.phone,
            "user_nickname": u.user_nickname,
            "user_realname": u.user_realname,
            "head_img": u.head_img,
            "password": u.password,
        }
        for u in users.values()
    ]
    return {"message": "success", "statusCode": "200", "data": data}


@router.get("/users/{user_id}")
async def get_user(user_id: str):
    users = load_users()
    user = users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail={"message": "user_not_found", "statusCode": "404"})
    return {
        "message": "success",
        "statusCode": "200",
        "data": {
            "user_id": user.user_id,
            "active": user.active,
            "phone": user.phone,
            "user_nickname": user.user_nickname,
            "user_realname": user.user_realname,
            "head_img": user.head_img,
            "password": user.password,
        },
    }


@router.post("/users")
async def create_user(request: Request):
    body = await request.json()
    phone = body.get("phone", "")
    password = body.get("password", "")
    user_nickname = body.get("user_nickname", "")
    user_realname = body.get("user_realname", "")
    active = body.get("active", True)

    if not phone or not password:
        raise HTTPException(status_code=400, detail={"message": "phone_and_password_required", "statusCode": "400"})

    users = load_users()
    user_id = str(uuid.uuid4())[:8]

    users[user_id] = UserRecord(
        user_id=user_id,
        active=active,
        phone=phone,
        password=password,
        user_nickname=user_nickname,
        user_realname=user_realname or None,
        head_img="",
    )
    await save_users_async(users)
    logger.info("创建用户: user_id={} phone={}", user_id, phone)

    return {"message": "success", "statusCode": "200", "data": {"user_id": user_id}}


@router.put("/users/{user_id}")
async def update_user(user_id: str, request: Request):
    users = load_users()
    user = users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail={"message": "user_not_found", "statusCode": "404"})

    body = await request.json()

    if "phone" in body:
        user.phone = body["phone"]
    if body.get("password"):
        user.password = body["password"]
    if "user_nickname" in body:
        user.user_nickname = body["user_nickname"]
    if "user_realname" in body:
        user.user_realname = body["user_realname"] or None
    if "active" in body:
        user.active = body["active"]
    if "head_img" in body:
        user.head_img = body["head_img"]

    users[user_id] = user
    await save_users_async(users)
    logger.info("更新用户: user_id={}", user_id)

    return {"message": "success", "statusCode": "200"}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str):
    users = load_users()
    if user_id not in users:
        raise HTTPException(status_code=404, detail={"message": "user_not_found", "statusCode": "404"})

    del users[user_id]
    save_users(users)
    logger.info("删除用户: user_id={}", user_id)

    return {"message": "success", "statusCode": "200"}


@router.get("/settings")
async def get_settings():
    settings = load_appsettings()
    return {"message": "success", "statusCode": "200", "data": settings}


@router.put("/settings")
async def update_settings(request: Request):
    body = await request.json()
    write_config(body)
    logger.info("更新设置")

    return {"message": "success", "statusCode": "200"}


@router.delete("/cache")
async def delete_cache():
    await clear_cache()
    logger.info("清除缓存")
    return {"message": "success", "statusCode": "200"}
