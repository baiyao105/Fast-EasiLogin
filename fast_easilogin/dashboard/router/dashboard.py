"""仪表盘路由"""

import time as _time

from fastapi import APIRouter

from fast_easilogin.api.gateway.state import get_login_trends, get_recent_logins, get_stats
from fast_easilogin.dashboard.models import ApiResponse
from fast_easilogin.storage import load_appsettings_model
from fast_easilogin.storage.models import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """获取仪表盘统计数据"""
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


@router.get("/recent-logins")
async def get_recent_logins_api(limit: int = 20):
    """获取最近登录记录"""
    records = get_recent_logins(limit)
    return ApiResponse(data=records)


@router.get("/login-trends")
async def get_login_trends_api(hours: int = 24):
    """获取登录趋势数据"""
    trends = get_login_trends(hours)
    return ApiResponse(data=trends)
