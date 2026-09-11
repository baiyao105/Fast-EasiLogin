from fastapi import APIRouter

from fast_easilogin.dashboard.v1.routers.accounts import router as accounts_router
from fast_easilogin.dashboard.v1.routers.auth import router as auth_router
from fast_easilogin.dashboard.v1.routers.debug import router as debug_router
from fast_easilogin.dashboard.v1.routers.events import router as events_router
from fast_easilogin.dashboard.v1.routers.login_events import router as login_events_router
from fast_easilogin.dashboard.v1.routers.service import router as service_router
from fast_easilogin.dashboard.v1.routers.settings import router as settings_router
from fast_easilogin.dashboard.v1.routers.settings import security_router
from fast_easilogin.dashboard.v1.routers.setup import router as setup_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(accounts_router)
router.include_router(settings_router)
router.include_router(security_router)
router.include_router(service_router)
router.include_router(events_router)
router.include_router(login_events_router)
router.include_router(debug_router)
router.include_router(setup_router)
