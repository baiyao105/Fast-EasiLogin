from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger
from starlette.staticfiles import StaticFiles

from fast_easilogin.core.constants import ALLOWED_ORIGINS
from fast_easilogin.core.services import Services
from fast_easilogin.dashboard.router import api_router, ws_router

_STATIC_DIR = Path(__file__).resolve().parent.parent / "assets" / "static"


def create_app(services: Services) -> FastAPI:
    app = FastAPI(
        title="EasiLogin Dashboard",
        description="EasiLogin",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.state.services = services

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

    logger.debug("Dashboard app created")
    return app
