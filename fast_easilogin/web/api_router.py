import time as _time
from typing import Any

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

from fast_easilogin.api.gateway.state import get_login_trends, get_recent_logins, get_stats
from fast_easilogin.storage import clear_cache, load_appsettings_model, load_users_async, save_users_async
from fast_easilogin.storage.config_manager import AppSettingsManager
from fast_easilogin.storage.models import (
    DashboardStats,
    OkResponse,
    SettingsUpdate,
    UserRecord,
)

router = APIRouter(prefix="/api")


class AddAccountBody(BaseModel):
    """添加账户请求"""

    userid: str
    password: str
    user_name: str = ""
    head_img: str = ""


def ok_response(data: dict | list | None = None) -> dict[str, Any]:
    """构造成功响应"""
    r: dict[str, Any] = {"message": "success", "statusCode": "200"}
    if data is not None:
        r["data"] = data
    return r


@router.get("/dashboard/stats", response_model=DashboardStats)
async def dashboard_stats():
    """统计"""
    stats = get_stats()
    settings = load_appsettings_model()
    return DashboardStats(
        service_status="running",
        uptime_seconds=int(_time.time() - stats["start_time"]),
        listen_port=settings.Global.port,
        total_logins=stats["total_logins"],
        success_logins=stats["success_logins"],
        failed_logins=stats["failed_logins"],
    )


@router.get("/dashboard/recent-logins")
async def dashboard_recent_logins(limit: int = 20):
    """最近登录记录"""
    records = get_recent_logins(limit)
    return ok_response(records)


@router.get("/dashboard/login-trends")
async def dashboard_login_trends(hours: int = 24):
    """登录趋势"""
    trends = get_login_trends(hours)
    return ok_response(trends)


@router.get("/settings")
async def get_settings():
    """获取配置"""
    settings = load_appsettings_model()
    return ok_response(settings.model_dump())


@router.post("/settings")
async def update_settings(body: SettingsUpdate):
    """更新配置"""
    manager = AppSettingsManager()
    current = manager.load()
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        return ok_response()

    current_dict = current.model_dump()
    if "Global" in current_dict:
        for k, v in update_data.items():
            if v is not None:
                current_dict["Global"][k] = v

    manager.write(current_dict)
    return ok_response({"message": "settings_updated"})


@router.post("/settings/clear-cache")
async def clear_cache_endpoint():
    """清空缓存"""
    await clear_cache()
    return ok_response({"message": "cache_cleared"})


@router.get("/accounts")
async def list_accounts():
    """账户列表"""
    users = await load_users_async()
    data = [
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
    return ok_response(data)


@router.post("/accounts")
async def add_account(body: AddAccountBody):
    """添加账户"""
    userid = body.userid.strip()
    password = body.password
    if not userid or not password:
        raise HTTPException(status_code=400, detail={"message": "userid and password required"})
    users = await load_users_async()
    users[userid] = UserRecord(
        user_id=userid,
        active=True,
        phone=userid,
        password=password,
        user_nickname=body.user_name,
        user_realname="",
        head_img=body.head_img,
        pt_timestamp=None,
    )
    await save_users_async(users, user_ids=[userid])
    logger.info("Web 添加账户: user_id={}", userid)
    return ok_response({"message": "account_added"})


@router.delete("/accounts/{userid}", response_model=OkResponse)
async def delete_account(userid: str):
    """删除账户"""
    users = await load_users_async()
    if userid not in users:
        raise HTTPException(status_code=404, detail={"message": "user_not_found", "statusCode": "404"})
    del users[userid]
    await save_users_async(users)
    logger.info("Web 删除账户: user_id={}", userid)
    return ok_response({"message": "account_deleted"})


@router.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "service": "webui"}
