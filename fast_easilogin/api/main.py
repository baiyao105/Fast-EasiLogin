from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from fast_easilogin.api.gateway.router import router
from fast_easilogin.core.constants import ALLOWED_ORIGINS
from fast_easilogin.core.errors import LoginFailedError, NetworkError
from fast_easilogin.core.runtime_state import RuntimeState
from fast_easilogin.core.services import Services
from fast_easilogin.storage import close_db, init_db


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

    yield

    await http_client.aclose()
    await close_db()
    logger.info("应用停止")


def create_app() -> FastAPI:
    app = FastAPI(title="FastLogin", lifespan=lifespan)

    @app.exception_handler(LoginFailedError)
    async def login_failed_handler(request: Request, exc: LoginFailedError):
        return JSONResponse(status_code=401, content={"message": str(exc), "statusCode": "401"})

    @app.exception_handler(NetworkError)
    async def network_error_handler(request: Request, exc: NetworkError):
        return JSONResponse(status_code=504, content={"message": str(exc), "statusCode": "504"})

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.include_router(router)

    return app
