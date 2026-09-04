from __future__ import annotations

import asyncio
import contextlib
import signal

from loguru import logger

from fast_easilogin.app.bootstrap import bootstrap
from fast_easilogin.app.mode import parse_mode
from fast_easilogin.app.runtime import AppRuntime, ServerConfig
from fast_easilogin.app.utils import install_global_handlers, setup_win_eventlog
from fast_easilogin.core.startup import check_ports, load_app_settings_sync


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
            service_args=[arg for arg in argv if arg != "--install-by-service"],
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

    settings = load_app_settings_sync()
    if settings is None:
        raise RuntimeError("无法加载配置")

    enable_eventlog = settings.global_settings.enable_eventlog
    report_event = setup_win_eventlog(enable_eventlog)
    install_global_handlers(report_event)

    api_port = settings.global_settings.port
    dashboard_port = settings.global_settings.webui_port
    check_ports(api_port, None if mode.only_service else dashboard_port)

    api_cfg = ServerConfig(host="0.0.0.0", port=api_port)
    dashboard_cfg = None if mode.only_service else ServerConfig(host="127.0.0.1", port=dashboard_port)

    async def _serve() -> None:
        runtime = AppRuntime()
        await runtime.start(api_cfg, dashboard_cfg, enable_eventlog)

        loop = asyncio.get_running_loop()

        def _shutdown_handler() -> None:
            logger.info("应用关闭...")
            runtime.stop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(sig, _shutdown_handler)
        await runtime.run()

    asyncio.run(_serve())
