from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not hasattr(app.state, "services"):
        raise RuntimeError("Application services were not initialized")  # noqa: TRY003

    logger.info("{} 创建", app.title)
    yield

    logger.info("{} 停止", app.title)
