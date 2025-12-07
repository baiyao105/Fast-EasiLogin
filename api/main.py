import asyncio
import contextlib

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse

from api.gateway.router import router
from api.gateway.state import token_renew_job
from api.user_auth.auth_service import close_http_client, init_http_client
from shared.storage import clear_cache, close_cache

app = FastAPI(default_response_class=ORJSONResponse)


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


@app.on_event("startup")
async def _startup():
    await init_http_client()
    await clear_cache()
    with contextlib.suppress(Exception):
        app.state.token_renew = asyncio.create_task(token_renew_job())


@app.on_event("shutdown")
async def _shutdown():
    await close_http_client()
    await clear_cache()
    await close_cache()
    with contextlib.suppress(Exception):
        t = getattr(app.state, "token_renew", None)
        if t:
            t.cancel()
