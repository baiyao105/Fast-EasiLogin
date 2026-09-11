from __future__ import annotations

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fast_easilogin.core.api_capture import ApiCaptureStore
from fast_easilogin.core.event_bus import EventBus
from fast_easilogin.core.runtime_state import RuntimeState
from fast_easilogin.storage.encryption.base import CredentialEncryptor


class Services:
    """共享服务容器"""

    __slots__ = (
        "api_capture",
        "dashboard_host",
        "db_factory",
        "encryptor",
        "event_bus",
        "http",
        "listen_port",
        "runtime_controller",
        "state",
    )

    def __init__(  # noqa: PLR0917
        self,
        http: httpx.AsyncClient,
        state: RuntimeState,
        listen_port: int = 24300,
        encryptor: CredentialEncryptor | None = None,
        event_bus: EventBus | None = None,
        runtime_controller: object | None = None,
        dashboard_host: str = "127.0.0.1",
        db_factory: async_sessionmaker[AsyncSession] | None = None,
        api_capture: ApiCaptureStore | None = None,
    ) -> None:
        self.http = http
        self.state = state
        self.listen_port = listen_port
        self.encryptor = encryptor
        self.event_bus = event_bus or EventBus()
        self.runtime_controller = runtime_controller
        self.dashboard_host = dashboard_host
        self.db_factory = db_factory
        self.api_capture = api_capture or ApiCaptureStore()
