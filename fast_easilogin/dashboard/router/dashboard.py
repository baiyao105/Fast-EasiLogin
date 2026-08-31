"""仪表盘路由"""

import time as _time

from fastapi import APIRouter, Request

from fast_easilogin.core.runtime_state import RuntimeState
from fast_easilogin.dashboard.models import ApiResponse
from fast_easilogin.storage import load_appsettings_model
from fast_easilogin.storage.models import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(request: Request):
    """统计数据"""
    state: RuntimeState = request.app.state.services.state
    stats = state.get_stats()
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
async def get_recent_logins_api(request: Request, limit: int = 20):
    """最近登录记录"""
    state: RuntimeState = request.app.state.services.state
    records = state.get_recent_logins(limit)
    return ApiResponse(data=records)


@router.get("/login-trends")
async def get_login_trends_api(request: Request, hours: int = 24):
    """登录趋势"""
    state: RuntimeState = request.app.state.services.state
    trends = state.get_login_trends(hours)
    return ApiResponse(data=trends)
