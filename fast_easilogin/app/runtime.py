from __future__ import annotations

import asyncio
import threading

import httpx
from granian.constants import Interfaces
from granian.log import LogLevels
from granian.server.embed import Server as GranianServer
from loguru import logger

from fast_easilogin.api.main import create_app as create_api_app
from fast_easilogin.core.runtime_state import RuntimeState
from fast_easilogin.core.services import Services
from fast_easilogin.dashboard.app import create_app as create_dashboard_app
from fast_easilogin.storage.config_manager import load_appsettings_model
from fast_easilogin.storage.kv_cache import get_cache


class ServerConfig:
    __slots__ = ("host", "port")

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port


class AppRuntime:
    """统一管理两个 Granian Server 的生命周期。"""

    __slots__ = (
        "_stop_event",
        "_thread_stop",
        "api_server",
        "dashboard_server",
        "services",
    )

    def __init__(self) -> None:
        self.api_server: GranianServer | None = None
        self.dashboard_server: GranianServer | None = None
        self.services: Services | None = None
        self._stop_event: asyncio.Event | None = None
        self._thread_stop: threading.Event = threading.Event()

    async def start(self, api_cfg: ServerConfig, dashboard_cfg: ServerConfig) -> None:
        settings = load_appsettings_model()

        # 创建共享服务
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=1.0, read=3.0, write=3.0, pool=10.0),
            limits=httpx.Limits(max_keepalive_connections=100, max_connections=500),
            http2=True,
        )
        state = RuntimeState()
        cache = get_cache()
        self.services = Services(http=http_client, state=state, cache=cache)

        # 创建 FastAPI Apps
        api_app = create_api_app(self.services)
        dashboard_app = create_dashboard_app(self.services)

        # 端口检查
        if not _is_port_available(api_cfg.host, api_cfg.port):
            raise RuntimeError(f"API 端口 {api_cfg.port} 已被占用")
        if not _is_port_available(dashboard_cfg.host, dashboard_cfg.port):
            raise RuntimeError(f"Dashboard 端口 {dashboard_cfg.port} 已被占用")

        # 创建 Granian Servers
        access_log = settings.Global.enable_eventlog
        self.api_server = GranianServer(
            api_app,
            address=api_cfg.host,
            port=api_cfg.port,
            interface=Interfaces.ASGI,
            log_enabled=True,
            log_access=access_log,
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

    async def run(self, stop_event: asyncio.Event | None = None) -> None:
        """并发运行两个 Server，直到 stop 被调用。"""
        self._stop_event = stop_event
        try:
            assert self.api_server is not None
            assert self.dashboard_server is not None
            await asyncio.gather(
                self.api_server.serve(),
                self.dashboard_server.serve(),
            )
        finally:
            await self.shutdown()

    def stop(self) -> None:
        """通知 Runtime 停止（可跨线程调用）。"""
        self._thread_stop.set()
        if self.api_server is not None:
            self.api_server.stop()
        if self.dashboard_server is not None:
            self.dashboard_server.stop()
        if self._stop_event is not None:
            self._stop_event.set()

    async def shutdown(self) -> None:
        """清理共享资源。"""
        if self.services is None:
            return
        await self.services.http.aclose()
        await self.services.cache.clear()
        self.services = None
        logger.info("服务已停止")


def _is_port_available(host: str, port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
        except OSError:
            return False
        else:
            return True
