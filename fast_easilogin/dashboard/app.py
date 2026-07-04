"""Dashboard FastAPI 应用"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger
from starlette.staticfiles import StaticFiles

from fast_easilogin.core.basic_dir import ensure_data_dirs
from fast_easilogin.core.constants import ALLOWED_ORIGINS
from fast_easilogin.core.http_client import close_http_client, init_http_client
from fast_easilogin.dashboard.router import api_router, ws_router
from fast_easilogin.storage import clear_cache, close_cache, load_appsettings_model

_STATIC_DIR = Path(__file__).resolve().parent.parent / "assets" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_data_dirs()
    await init_http_client()
    await clear_cache()
    settings = load_appsettings_model()
    logger.success("Dashboard 启动成功: http://127.0.0.1:{}", settings.Global.webui_port)
    yield
    await close_http_client()
    await clear_cache()
    await close_cache()


app = FastAPI(
    title="Fast EasiLogin Dashboard API",
    description="希沃快速登录服务控制台 API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
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
    """健康检查"""
    return {"status": "ok", "service": "dashboard"}


# 挂载静态文件 (必须在所有路由之后)
if _STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
