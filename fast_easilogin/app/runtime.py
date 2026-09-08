from __future__ import annotations

import asyncio

import httpx
from granian.constants import Interfaces
from granian.log import LogLevels
from granian.server.embed import Server as GranianServer
from loguru import logger

from fast_easilogin.api.main import create_app as create_api_app
from fast_easilogin.core.event_bus import EventBus
from fast_easilogin.core.runtime_state import RuntimeState
from fast_easilogin.core.services import Services
from fast_easilogin.dashboard.app import create_app as create_dashboard_app
from fast_easilogin.storage import close_db, init_db
from fast_easilogin.storage.database import get_session_factory
from fast_easilogin.storage.encryption.factory import create_encryptor
from fast_easilogin.storage.store import initialize_settings


class ServerConfig:
    __slots__ = ("host", "port")

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port


class AppRuntime:
    __slots__ = ("_maintenance_task", "_stopped", "api_server", "dashboard_server", "services")

    def __init__(self) -> None:
        self.api_server: GranianServer | None = None
        self.dashboard_server: GranianServer | None = None
        self.services: Services | None = None
        self._stopped = False

    async def start(
        self,
        api_cfg: ServerConfig,
        dashboard_cfg: ServerConfig | None,
        enable_eventlog: bool = True,
    ) -> None:
        try:
            await init_db()
            async with get_session_factory()() as db:
                settings = await initialize_settings(db)
                await db.commit()
            http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=1.0, read=3.0, write=3.0, pool=10.0),
                limits=httpx.Limits(max_keepalive_connections=100, max_connections=500),
                http2=True,
            )
            self.services = Services(
                http=http_client,
                state=RuntimeState(),
                listen_port=api_cfg.port,
                dashboard_host=dashboard_cfg.host if dashboard_cfg is not None else "127.0.0.1",
                encryptor=create_encryptor(
                    settings.global_settings.encryption_key_source, settings.global_settings.encryption_key_version
                ),
                event_bus=EventBus(),
                db_factory=get_session_factory(),
                runtime_controller=self,
            )
            api_app = create_api_app(self.services)
            dashboard_app = create_dashboard_app(self.services) if dashboard_cfg is not None else None

            self.api_server = GranianServer(
                api_app,
                address=api_cfg.host,
                port=api_cfg.port,
                interface=Interfaces.ASGI,
                log_enabled=True,
                log_access=enable_eventlog,
                log_level=LogLevels.info,
            )
            if dashboard_cfg is not None and dashboard_app is not None:
                self.dashboard_server = GranianServer(
                    dashboard_app,
                    address=dashboard_cfg.host,
                    port=dashboard_cfg.port,
                    interface=Interfaces.ASGI,
                    log_enabled=True,
                    log_level=LogLevels.info,
                )
        except BaseException:
            if self.services is not None:
                await self.services.event_bus.close()
                await self.services.http.aclose()
                self.services = None
            await close_db()
            raise

        logger.debug(
            "服务启动: api=http://{}:{} dashboard={}",
            api_cfg.host,
            api_cfg.port,
            f"http://{dashboard_cfg.host}:{dashboard_cfg.port}" if dashboard_cfg else "disabled",
        )

    async def run(self) -> None:
        assert self.api_server is not None
        api_task = asyncio.create_task(self.api_server.serve())
        dashboard_task = (
            asyncio.create_task(self.dashboard_server.serve()) if self.dashboard_server is not None else None
        )
        tasks = [api_task] + ([dashboard_task] if dashboard_task is not None else [])
        try:
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in done:
                exception = task.exception()
                if exception is not None:
                    self.stop()
                    await asyncio.gather(*pending, return_exceptions=True)
                    raise exception
            self.stop()
            await asyncio.gather(*pending)
        finally:
            self.stop()
            await asyncio.gather(*tasks, return_exceptions=True)
            if self.services is not None:
                await self.services.event_bus.close()
                await self.services.http.aclose()
                self.services = None
            await close_db()

    def stop(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        if self.api_server is not None:
            self.api_server.stop()
        if self.dashboard_server is not None:
            self.dashboard_server.stop()

    def restart(self) -> None:
        """supervisor管理重启"""
        self.stop()

    def status(self) -> str:
        return "stopped" if self._stopped else "running"
