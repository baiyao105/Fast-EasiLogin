from __future__ import annotations

import httpx

from fast_easilogin.core.runtime_state import RuntimeState


class Services:
    """共享服务容器"""

    __slots__ = ("http", "listen_port", "state")

    def __init__(self, http: httpx.AsyncClient, state: RuntimeState, listen_port: int = 24300) -> None:
        self.http = http
        self.state = state
        self.listen_port = listen_port
