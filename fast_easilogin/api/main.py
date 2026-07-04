from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from fast_easilogin.api.gateway.router import router
from fast_easilogin.app.utils import stop_server
from fast_easilogin.core.basic_dir import ensure_data_dirs
from fast_easilogin.core.constants import ALLOWED_ORIGINS
from fast_easilogin.core.errors import LoginFailedError, NetworkError
from fast_easilogin.core.http_client import close_http_client, init_http_client
from fast_easilogin.storage import clear_cache, close_cache, load_appsettings_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_data_dirs()
    await init_http_client()
    await clear_cache()
    settings = load_appsettings_model()
    srv_port = int(settings.Global.port)
    logger.success("服务启动成功: url=http://{}:{}", "127.0.0.1", srv_port)
    yield
    stop_server()
    await close_http_client()
    await clear_cache()
    await close_cache()


app = FastAPI(lifespan=lifespan)


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


if __name__ == "__main__":
    import asyncio

    from granian.constants import Interfaces
    from granian.server.embed import Server as GranianServer

    _s = load_appsettings_model()
    server = GranianServer(
        app,
        address="127.0.0.1",
        port=int(_s.Global.port),
        interface=Interfaces.ASGI,
        log_enabled=False,
    )
    asyncio.run(server.serve())
