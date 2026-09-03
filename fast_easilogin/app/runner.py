from __future__ import annotations

import asyncio
import socket

from fast_easilogin.app.bootstrap import bootstrap
from fast_easilogin.app.mode import parse_mode
from fast_easilogin.app.runtime import AppRuntime, ServerConfig
from fast_easilogin.app.utils import install_global_handlers, setup_win_eventlog
from fast_easilogin.storage import load_settings
from fast_easilogin.storage.database import get_db, init_db


def _is_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
        except OSError:
            return False
        else:
            return True


async def _load_settings():
    await init_db()
    async for db in get_db():
        return await load_settings(db)
    return None


def run(argv: list[str] | None = None) -> None:
    if argv is None:
        import sys

        argv = sys.argv[1:]

    if "--install-by-service" in argv:
        from fast_easilogin.core.service_manager import WindowsServiceManager

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
        from fast_easilogin.core.service_manager import WindowsServiceManager

        WindowsServiceManager.remove("SeewoFastLoginService")
        return

    mode = parse_mode(argv)
    bootstrap(log_level=mode.log_level)

    settings = asyncio.run(_load_settings())
    if settings is None:
        raise RuntimeError("无法加载配置")

    enable_eventlog = settings.global_settings.enable_eventlog
    report_event = setup_win_eventlog(enable_eventlog)
    install_global_handlers(report_event)

    api_cfg = ServerConfig(host="0.0.0.0", port=settings.global_settings.port)
    dashboard_cfg = ServerConfig(host="127.0.0.1", port=settings.global_settings.webui_port)

    if not _is_port_available(api_cfg.host, api_cfg.port):
        raise RuntimeError(f"端口 {api_cfg.port} 已被占用")  # noqa: TRY003
    if not _is_port_available(dashboard_cfg.host, dashboard_cfg.port):
        raise RuntimeError(f"Dashboard端口 {dashboard_cfg.port} 已被占用")  # noqa: TRY003

    runtime = AppRuntime()
    runtime.start(api_cfg, dashboard_cfg, enable_eventlog)
    asyncio.run(runtime.run())
