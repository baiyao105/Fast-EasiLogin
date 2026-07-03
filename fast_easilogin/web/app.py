from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

_STATIC = Path(__file__).resolve().parent.parent / "assets" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not _STATIC.exists():
        logger.warning("Web static directory not found: {}", _STATIC)
    else:
        logger.info("Web service initialized")
    yield


app = FastAPI(lifespan=lifespan)

# 挂载静态文件
app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


@app.get("/{path:path}")
async def serve_spa(path: str):
    """SPA 路由

    非文件请求返回 index.html 交给前端路由处理
    """
    file_path = _STATIC / path
    if file_path.is_file():
        return FileResponse(file_path)

    index_file = _STATIC / "index.html"
    if not index_file.is_file():
        return JSONResponse(status_code=503, content={"error": "index.html not found"})
    return FileResponse(index_file)
