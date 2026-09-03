from __future__ import annotations

import time as _time

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from fast_easilogin.core.runtime_state import RuntimeState
from fast_easilogin.dashboard.models import ApiResponse
from fast_easilogin.storage import get_db
from fast_easilogin.storage.models import DashboardStats
from fast_easilogin.storage.store import load_settings

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(request: Request, db: AsyncSession = Depends(get_db)):
    state: RuntimeState = request.app.state.services.state
    stats = state.get_stats()
    settings = await load_settings(db)
    return DashboardStats(
        service_status="running",
        uptime_seconds=int(_time.time() - stats["start_time"]),
        listen_port=settings.global_settings.port,
        total_logins=stats["total_logins"],
        success_logins=stats["success_logins"],
        failed_logins=stats["failed_logins"],
    )


@router.get("/recent-logins")
async def get_recent_logins_api(request: Request, limit: int = 20):
    state: RuntimeState = request.app.state.services.state
    records = state.get_recent_logins(limit)
    return ApiResponse(data=records)


@router.get("/login-trends")
async def get_login_trends_api(request: Request, hours: int = 24):
    state: RuntimeState = request.app.state.services.state
    trends = state.get_login_trends(hours)
    return ApiResponse(data=trends)
