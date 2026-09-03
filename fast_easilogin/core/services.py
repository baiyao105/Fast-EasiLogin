from __future__ import annotations

import httpx

from fast_easilogin.core.runtime_state import RuntimeState


class Services:
    """共享服务容器"""

    __slots__ = ("http", "state")

    def __init__(self, http: httpx.AsyncClient, state: RuntimeState) -> None:
        self.http = http
        self.state = state
