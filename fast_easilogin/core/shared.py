"""一些共享资源"""

from __future__ import annotations

import httpx

from fast_easilogin.core.runtime_state import RuntimeState

_http_client: httpx.AsyncClient | None = None
_state: RuntimeState | None = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client  # noqa: PLW0603
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=1.0, read=3.0, write=3.0, pool=10.0),
            limits=httpx.Limits(max_keepalive_connections=100, max_connections=500),
            http2=True,
        )
    return _http_client


def get_state() -> RuntimeState:
    global _state  # noqa: PLW0603
    if _state is None:
        _state = RuntimeState()
    return _state


async def close_shared_resources() -> None:
    global _http_client, _state  # noqa: PLW0603
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
    _state = None
