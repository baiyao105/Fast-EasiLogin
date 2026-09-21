from __future__ import annotations

import asyncio

from fast_easilogin.app.bootstrap import bootstrap
from fast_easilogin.app.mode import parse_mode
from fast_easilogin.app.runtime import AppRuntime, ServerConfig
from fast_easilogin.app.utils import install_global_handlers, setup_win_eventlog
from fast_easilogin.storage import load_appsettings_model


async def _run(runtime: AppRuntime) -> None:
    """主协程"""
    stop_event = asyncio.Event()
    try:
        settings = load_appsettings_model()
        api_cfg = ServerConfig(host="0.0.0.0", port=settings.Global.port)
        dashboard_cfg = ServerConfig(host="127.0.0.1", port=settings.Global.webui_port)

        await runtime.start(api_cfg, dashboard_cfg)
        await runtime.run(stop_event)
    finally:
        await runtime.shutdown()


def run(argv: list[str] | None = None) -> None:
    """同步入口"""
    if argv is None:
        import sys

        argv = sys.argv[1:]

    # 服务安装/卸载是一次性操作
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

    settings = load_appsettings_model()
    enable_eventlog = settings.Global.enable_eventlog
    report_event = setup_win_eventlog(enable_eventlog)
    install_global_handlers(report_event)

    runtime = AppRuntime()
    asyncio.run(_run(runtime))
