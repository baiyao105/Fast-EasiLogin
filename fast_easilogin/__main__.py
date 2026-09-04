from __future__ import annotations

import sys

from fast_easilogin.app.runner import run


def main():
    run()


if sys.platform == "win32":
    import asyncio
    import threading

    import win32event
    import win32service

    from fast_easilogin.app.bootstrap import bootstrap
    from fast_easilogin.app.mode import parse_mode, service_argv
    from fast_easilogin.app.runtime import AppRuntime, ServerConfig
    from fast_easilogin.app.utils import install_global_handlers, setup_win_eventlog
    from fast_easilogin.core.service_manager import WindowsServiceBase
    from fast_easilogin.core.startup import check_ports, load_app_settings_sync

    _runtime: AppRuntime | None = None
    _runtime_lock = threading.Lock()
    _stop_requested = False

    class AppService(WindowsServiceBase):
        _svc_name_ = "SeewoFastLoginService"
        _svc_display_name_ = "Seewo FastLogin Service"
        _svc_description_ = "Seewo FastLogin background service"

        def SvcStop(self):
            global _stop_requested  # noqa: PLW0603
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            with _runtime_lock:
                _stop_requested = True
                if _runtime is not None:
                    _runtime.stop()
            win32event.SetEvent(self.hWaitStop)

        def SvcDoRun(self):
            global _runtime, _stop_requested  # noqa: PLW0603
            argv = service_argv(sys.argv[1:])
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

            runtime = AppRuntime()

            async def _serve() -> None:
                await runtime.start(api_cfg, dashboard_cfg, enable_eventlog)
                with _runtime_lock:
                    _runtime = runtime
                    requested = _stop_requested
                if requested:
                    runtime.stop()
                await runtime.run()

            try:
                asyncio.run(_serve())
            finally:
                with _runtime_lock:
                    _runtime = None
                    _stop_requested = False


if __name__ == "__main__":
    main()
