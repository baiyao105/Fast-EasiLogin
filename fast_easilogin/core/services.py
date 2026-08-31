from __future__ import annotations

import httpx

from fast_easilogin.core.runtime_state import RuntimeState
from fast_easilogin.storage.kv_cache import InMemoryKVCache


class Services:
    """共享服务容器(进程内)"""

    __slots__ = ("cache", "http", "state")

    def __init__(self, http: httpx.AsyncClient, state: RuntimeState, cache: InMemoryKVCache) -> None:
        self.http = http
        self.state = state
        self.cache = cache
