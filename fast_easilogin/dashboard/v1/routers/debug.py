from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from fast_easilogin.dashboard.v1.auth import require_dashboard_auth

router = APIRouter(prefix="/debug", tags=["debug"], dependencies=[Depends(require_dashboard_auth)])


def _store(request: Request):
    services = getattr(request.app.state, "services", None)
    store = getattr(services, "api_capture", None) if services else None
    if store is None:
        raise HTTPException(status_code=503, detail="capture_unavailable")
    return store


@router.get("/captures")
async def list_captures(
    request: Request,
    limit: int = Query(default=100, ge=1, le=200),
    path: str | None = Query(default=None, description="按 path 子串过滤"),
):
    store = _store(request)
    return {"enabled": store.enabled, "items": store.list_items(limit=limit, path_contains=path)}


@router.post("/captures/clear")
async def clear_captures(request: Request):
    store = _store(request)
    store.clear()
    return {"cleared": True}


@router.post("/captures/enabled")
async def set_capture_enabled(request: Request, enabled: bool = Query(default=True)):
    store = _store(request)
    store.set_enabled(enabled)
    return {"enabled": store.enabled}
