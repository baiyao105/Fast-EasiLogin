"""路由汇总"""

from fastapi import APIRouter

from fast_easilogin.dashboard.router.accounts import router as accounts_router
from fast_easilogin.dashboard.router.dashboard import router as dashboard_router
from fast_easilogin.dashboard.router.settings import router as settings_router
from fast_easilogin.dashboard.router.websocket import router as ws_router

api_router = APIRouter(prefix="/api")
api_router.include_router(dashboard_router)
api_router.include_router(settings_router)
api_router.include_router(accounts_router)

# WebSocket 路由 (不在 /api 前缀下)
__all__ = ["api_router", "ws_router"]
