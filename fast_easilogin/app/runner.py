from __future__ import annotations

import socket
import sys
import threading
import time
import webbrowser

import uvicorn
from loguru import logger

from fast_easilogin.api.main import app
from fast_easilogin.app.bootstrap import bootstrap
from fast_easilogin.app.mode import parse_mode
from fast_easilogin.app.utils import install_global_handlers, set_server, setup_logging, setup_win_eventlog
from fast_easilogin.core.service_manager import WindowsServiceManager
from fast_easilogin.storage import load_appsettings_model
from fast_easilogin.web import run_web_server


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
            s.bind(("127.0.0.1", port))
        except OSError:
            return False
        else:
            return True


def _create_api_server(port: int, access_log: bool) -> uvicorn.Server:
    """创建服务"""
    config = uvicorn.Config(
        app, host="127.0.0.1", port=port, server_header=False, access_log=access_log, log_config=None
    )
    return uvicorn.Server(config)


def run_service(log_level: str = "INFO", access_log: bool = False) -> None:
    """api only"""
    _init_environment(log_level)
    port = load_appsettings_model().Global.port
    server = _create_api_server(port, access_log)
    set_server(server)
    server.run()


def run_webui(log_level: str = "INFO", access_log: bool = False, no_browser: bool = False) -> None:
    """完整服务"""
    _init_environment(log_level)
    settings = load_appsettings_model()
    port = settings.Global.port
    web_port = settings.Global.webui_port

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
        webbrowser.open(f"http://127.0.0.1:{web_port}")

    server = _create_api_server(port, access_log)
    set_server(server)
    server.run()


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
