from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from loguru import logger

from fast_easilogin.core.runtime_state import RuntimeState
from fast_easilogin.core.services import Services
from fast_easilogin.storage import close_db, init_db

_shared_http_client: httpx.AsyncClient | None = None
_shared_state: RuntimeState | None = None


def _get_or_create_http_client() -> httpx.AsyncClient:
    global _shared_http_client  # noqa: PLW0603
    if _shared_http_client is not None:
        return _shared_http_client
    _shared_http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=1.0, read=3.0, write=3.0, pool=10.0),
        limits=httpx.Limits(max_keepalive_connections=100, max_connections=500),
        http2=True,
    )
    return _shared_http_client


def _get_or_create_state() -> RuntimeState:
    global _shared_state  # noqa: PLW0603
    if _shared_state is not None:
        return _shared_state
    _shared_state = RuntimeState()
    return _shared_state


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    http_client = _get_or_create_http_client()
    state = _get_or_create_state()
    app.state.services = Services(http=http_client, state=state)

    logger.info("{} 创建", app.title)
    yield

    global _shared_http_client, _shared_state  # noqa: PLW0603
    if _shared_http_client is not None:
        await _shared_http_client.aclose()
        _shared_http_client = None
    _shared_state = None
    await close_db()
    logger.info("{} 停止", app.title)
