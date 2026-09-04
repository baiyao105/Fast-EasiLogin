from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from fast_easilogin.core.services import Services
from fast_easilogin.core.shared import get_http_client, get_state
from fast_easilogin.storage import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    app.state.services = Services(http=get_http_client(), state=get_state())

    logger.info("{} 创建", app.title)
    yield

    await close_db()
    logger.info("{} 停止", app.title)
