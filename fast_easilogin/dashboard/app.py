from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger
from starlette.staticfiles import StaticFiles

from fast_easilogin.core.constants import ALLOWED_ORIGINS
from fast_easilogin.core.runtime_state import RuntimeState
from fast_easilogin.core.services import Services
from fast_easilogin.dashboard.router import api_router, ws_router
from fast_easilogin.storage import close_db, init_db

_STATIC_DIR = Path(__file__).resolve().parent.parent / "assets" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=1.0, read=3.0, write=3.0, pool=10.0),
        limits=httpx.Limits(max_keepalive_connections=100, max_connections=500),
        http2=True,
    )
    state = RuntimeState()
    app.state.services = Services(http=http_client, state=state)

    logger.info("Dashboard 创建")
    yield

    await http_client.aclose()
    await close_db()
    logger.info("Dashboard 销毁")


def create_app() -> FastAPI:
    app = FastAPI(
        title="EasiLogin Dashboard",
        description="EasiLogin",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.include_router(api_router)
    app.include_router(ws_router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "dashboard"}

    if _STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")

    return app
