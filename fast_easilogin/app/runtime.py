from __future__ import annotations

import asyncio

from granian.constants import Interfaces
from granian.log import LogLevels
from granian.server.embed import Server as GranianServer
from loguru import logger

from fast_easilogin.api.main import create_app as create_api_app
from fast_easilogin.dashboard.app import create_app as create_dashboard_app


class ServerConfig:
    __slots__ = ("host", "port")

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port


class AppRuntime:
    __slots__ = ("api_server", "dashboard_server")

    def __init__(self) -> None:
        self.api_server: GranianServer | None = None
        self.dashboard_server: GranianServer | None = None

    def start(self, api_cfg: ServerConfig, dashboard_cfg: ServerConfig, enable_eventlog: bool = True) -> None:
        api_app = create_api_app()
        dashboard_app = create_dashboard_app()

        self.api_server = GranianServer(
            api_app,
            address=api_cfg.host,
            port=api_cfg.port,
            interface=Interfaces.ASGI,
            log_enabled=True,
            log_access=enable_eventlog,
            log_level=LogLevels.info,
        )
        self.dashboard_server = GranianServer(
            dashboard_app,
            address=dashboard_cfg.host,
            port=dashboard_cfg.port,
            interface=Interfaces.ASGI,
            log_enabled=True,
            log_level=LogLevels.info,
        )

        logger.success(
            "服务启动成功: api=http://{}:{} dashboard=http://{}:{}",
            api_cfg.host,
            api_cfg.port,
            dashboard_cfg.host,
            dashboard_cfg.port,
        )

    async def run(self) -> None:
        assert self.api_server is not None
        assert self.dashboard_server is not None
        await asyncio.gather(
            self.api_server.serve(),
            self.dashboard_server.serve(),
        )

    def stop(self) -> None:
        if self.api_server is not None:
            self.api_server.stop()
        if self.dashboard_server is not None:
            self.dashboard_server.stop()
