from __future__ import annotations

import json
import secrets
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles

from fast_easilogin.core.constants import ALLOWED_ORIGINS
from fast_easilogin.core.lifespan import lifespan
from fast_easilogin.core.services import Services
from fast_easilogin.dashboard.v1.router import router as v1_router

_STATIC_DIR = Path(__file__).resolve().parent.parent / "assets" / "static"


def create_app(services: Services | None = None) -> FastAPI:
    app = FastAPI(
        title="EasiLogin Dashboard",
        description="EasiLogin",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    if services is not None:
        app.state.services = services
        app.state.db_factory = services.db_factory

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.include_router(v1_router)

    @app.middleware("http")
    async def v1_envelope(request: Request, call_next):
        response = await call_next(request)
        if not request.url.path.startswith("/api/v1") or response.headers.get("content-type", "").startswith(
            "text/event-stream"
        ):
            return response
        body = b"".join([chunk async for chunk in response.body_iterator])
        try:
            data = json.loads(body) if body else None
        except json.JSONDecodeError:
            data = body.decode("utf-8", errors="replace")
        if isinstance(data, dict) and {"success", "data", "error", "request_id"}.issubset(data):
            return JSONResponse(data, status_code=response.status_code, headers=dict(response.headers))
        if response.status_code >= 400:  # noqa: PLR2004
            detail = data.get("detail", "request_failed") if isinstance(data, dict) else "request_failed"
            error = {
                "code": detail if isinstance(detail, str) else "request_failed",
                "message": str(detail),
                "details": None,
            }
            return JSONResponse(
                {"success": False, "data": None, "error": error, "request_id": secrets.token_urlsafe(12)},
                status_code=response.status_code,
            )
        return JSONResponse(
            {"success": True, "data": data, "error": None, "request_id": secrets.token_urlsafe(12)},
            status_code=response.status_code,
        )

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "dashboard"}

    if _STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")

    return app
