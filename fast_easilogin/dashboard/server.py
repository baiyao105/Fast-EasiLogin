"""Dashboard Granian 启动器"""

import asyncio
from contextlib import suppress

from granian.constants import Interfaces
from granian.log import LogLevels
from granian.server.embed import Server as GranianServer

from fast_easilogin.dashboard.app import app


def run_dashboard_server(port: int = 3000, log_level: str = "info") -> None:
    """启动 Dashboard 服务"""
    server = GranianServer(
        app,
        address="127.0.0.1",
        port=port,
        interface=Interfaces.ASGI,
        log_enabled=True,
        log_level=LogLevels(log_level),
    )
    with suppress(KeyboardInterrupt):
        asyncio.run(server.serve())
