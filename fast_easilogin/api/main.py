from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from fast_easilogin.api.gateway.router import router
from fast_easilogin.runtime.utils import stop_server
from fast_easilogin.shared.basic_dir import ensure_data_dirs
from fast_easilogin.shared.errors import LoginFailedError, NetworkError
from fast_easilogin.shared.http_client import close_http_client, init_http_client
from fast_easilogin.shared.store import clear_cache, close_cache, load_appsettings_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        ensure_data_dirs()
        await init_http_client()
        await clear_cache()
        settings = load_appsettings_model()
        srv_port = int(settings.Global.port)
        logger.success("服务启动成功: url=http://{}:{}", "127.0.0.1", srv_port)
    except Exception as e:
        logger.exception("服务启动失败: {}", e)
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=500)
app.include_router(router)

_STATIC = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC)), name="webui_static")


@app.get("/")
async def webui_index():
    return FileResponse(_STATIC / "index.html")


if __name__ == "__main__":
    import uvicorn

    _s = load_appsettings_model()
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=int(_s.Global.port),
        server_header=False,
        log_config=None,
    )
