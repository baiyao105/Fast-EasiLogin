import asyncio
import contextlib
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse
from loguru import logger

from api.gateway.router import router
from api.gateway.state import token_renew_job
from runtime.utils import stop
from shared.basic_dir import ensure_data_dirs
from shared.http_client import close_http_client, init_http_client
from shared.store.config import clear_cache, close_cache, load_appsettings_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_data_dirs()
    await init_http_client()
    await clear_cache()
    with contextlib.suppress(Exception):
        s_local = load_appsettings_model()
        app.state.token_renew = asyncio.create_task(token_renew_job(int(s_local.Global.token_check_interval)))
    try:
        s = load_appsettings_model()
        base_port = int(s.Global.port)
        listen_port = int(s.mitmproxy.listen_port)
        srv_port = base_port + 1 if listen_port == base_port else base_port
        logger.success("服务启动成功: url=http://{}:{}", "127.0.0.1", srv_port)
    except Exception as e:
        logger.exception(f"服务启动失败: {e}")
    try:
        yield
        stop()
    except asyncio.CancelledError:
        pass
    finally:
        await close_http_client()
        await clear_cache()
        await close_cache()
        t = getattr(app.state, "token_renew", None)
        if t:
            t.cancel()
            with suppress(asyncio.CancelledError):
                await t


app = FastAPI(default_response_class=ORJSONResponse, lifespan=lifespan)


@app.middleware("http")
async def add_global_headers(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,DELETE"
    response.headers["Content-Type"] = "application/json; charset=UTF-8"
    return response


app.add_middleware(GZipMiddleware, minimum_size=500)
app.include_router(router)
