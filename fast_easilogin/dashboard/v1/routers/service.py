from __future__ import annotations

from inspect import isawaitable

from fastapi import APIRouter, Depends, Request

from fast_easilogin.dashboard.v1.auth import require_dashboard_auth

router = APIRouter(prefix="/service", tags=["service"], dependencies=[Depends(require_dashboard_auth)])


@router.get("/status")
async def status(request: Request):
    controller = request.app.state.services.runtime_controller
    value = controller.status() if controller is not None and hasattr(controller, "status") else "running"
    if isawaitable(value):
        value = await value
    return {"status": value, "listen_port": request.app.state.services.listen_port}


@router.post("/restart", status_code=202)
async def restart(request: Request):
    controller = request.app.state.services.runtime_controller
    if controller is not None and hasattr(controller, "restart"):
        result = controller.restart()
        if isawaitable(result):
            await result
    return {"accepted": True, "action": "restart"}


@router.post("/stop", status_code=202)
async def stop(request: Request):
    controller = request.app.state.services.runtime_controller
    if controller is not None and hasattr(controller, "stop"):
        result = controller.stop()
        if isawaitable(result):
            await result
    return {"accepted": True, "action": "stop"}
