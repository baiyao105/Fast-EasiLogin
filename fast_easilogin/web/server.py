import asyncio
import contextlib

from granian.constants import Interfaces
from granian.log import LogLevels
from granian.server.embed import Server as GranianServer

from .app import app


def run_web_server(port: int = 3000, log_level: str = "info") -> None:
    """启动 WebUI 服务"""
    server = GranianServer(
        app,
        address="127.0.0.1",
        port=port,
        interface=Interfaces.ASGI,
        log_enabled=True,
        log_level=LogLevels(log_level),
    )
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(server.serve())
