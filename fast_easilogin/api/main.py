from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from fast_easilogin.api.gateway.router import router
from fast_easilogin.core.constants import ALLOWED_ORIGINS
from fast_easilogin.core.errors import LoginFailedError, NetworkError
from fast_easilogin.core.services import Services


def create_app(services: Services) -> FastAPI:
    app = FastAPI(title="FastLogin")
    app.state.services = services

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

    logger.debug("app created")
    return app
