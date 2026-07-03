from __future__ import annotations

import asyncio
import contextlib
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

from granian.constants import Interfaces
from granian.log import LogLevels
from granian.server.embed import Server as GranianServer
from loguru import logger

from fast_easilogin.api.main import app
from fast_easilogin.app.bootstrap import bootstrap
from fast_easilogin.app.mode import parse_mode
from fast_easilogin.app.utils import install_global_handlers, set_server, setup_logging, setup_win_eventlog
from fast_easilogin.core.service_manager import WindowsServiceManager
from fast_easilogin.storage import load_appsettings_model
from fast_easilogin.web import run_web_server

_STATIC_DIR = Path(__file__).resolve().parent.parent / "assets" / "static"


def _init_environment(log_level: str):
    setup_logging(file_level=log_level)
    settings = load_appsettings_model()
    enable_eventlog = settings.Global.enable_eventlog
    report_event = setup_win_eventlog(enable_eventlog)
    install_global_handlers(report_event)
    return report_event


def _is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
        except OSError:
            return False
        else:
            return True


def _create_api_server(port: int, access_log: bool) -> GranianServer:
    """创建服务"""
    return GranianServer(
        app,
        address="0.0.0.0",
        port=port,
        interface=Interfaces.ASGI,
        log_enabled=True,
        log_access=access_log,
        log_level=LogLevels.info,
    )


def run_service(log_level: str = "INFO", access_log: bool = False) -> None:
    """api only"""
    _init_environment(log_level)
    port = load_appsettings_model().Global.port
    server = _create_api_server(port, access_log)
    set_server(server)
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(server.serve())


def run_webui(log_level: str = "INFO", access_log: bool = False, no_browser: bool = False) -> None:
    """完整服务"""
    _init_environment(log_level)
    settings = load_appsettings_model()
    port = settings.Global.port
    web_port = settings.Global.webui_port

    if not _STATIC_DIR.exists():
        logger.error("控制台静态文件目录不存在: {}", _STATIC_DIR)
        run_service(log_level=log_level, access_log=access_log)
        return

    if not _is_port_available(port):
        logger.error("API 端口 {} 已被占用", port)
        return
    if not _is_port_available(web_port):
        logger.error("WebUI 端口 {} 已被占用", web_port)
        return

    web_thread = threading.Thread(target=run_web_server, args=(web_port, log_level.lower()), daemon=True)
    web_thread.start()

    time.sleep(0.5)

    if not no_browser:
        webbrowser.open(f"http://0.0.0.0:{web_port}")

    server = _create_api_server(port, access_log)
    set_server(server)
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(server.serve())


def run(argv: list[str] | None = None):
    if argv is None:
        argv = sys.argv[1:]

    # 服务安装/卸载是一次性操作
    if "--install-by-service" in argv:
        WindowsServiceManager.install(
            service_name="SeewoFastLoginService",
            module="fast_easilogin.__main__",
            klass="AppService",
            display_name="Seewo FastLogin Service",
            description="Seewo FastLogin background service",
        )
        WindowsServiceManager.set_autostart("SeewoFastLoginService", True)
        WindowsServiceManager.start("SeewoFastLoginService")
        return

    if "--uninstall-service" in argv:
        WindowsServiceManager.remove("SeewoFastLoginService")
        return

    mode = parse_mode(argv)
    bootstrap(log_level=mode.log_level)

    if mode.mode == "service":
        run_service(log_level=mode.log_level, access_log=mode.access_log)
    else:
        run_webui(
            log_level=mode.log_level,
            access_log=mode.access_log,
            no_browser=mode.no_browser,
        )
