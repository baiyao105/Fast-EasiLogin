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
    from fast_easilogin.app.runtime import AppRuntime, ServerConfig
    from fast_easilogin.app.utils import install_global_handlers, setup_win_eventlog
    from fast_easilogin.core.service_manager import WindowsServiceBase
    from fast_easilogin.storage import load_settings
    from fast_easilogin.storage.database import get_db, init_db

    _runtime: AppRuntime | None = None
    _runtime_lock = threading.Lock()

    class AppService(WindowsServiceBase):
        _svc_name_ = "SeewoFastLoginService"
        _svc_display_name_ = "Seewo FastLogin Service"
        _svc_description_ = "Seewo FastLogin background service"

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            with _runtime_lock:
                if _runtime is not None:
                    _runtime.stop()
            win32event.SetEvent(self.hWaitStop)

        def SvcDoRun(self):
            bootstrap(log_level="INFO")

            async def _init():
                await init_db()
                async for db in get_db():
                    return await load_settings(db)
                return None

            settings = asyncio.run(_init())
            if settings is None:
                raise RuntimeError("无法加载配置")

            enable_eventlog = settings.global_settings.enable_eventlog
            report_event = setup_win_eventlog(enable_eventlog)
            install_global_handlers(report_event)
            api_cfg = ServerConfig(host="0.0.0.0", port=settings.global_settings.port)
            dashboard_cfg = ServerConfig(host="127.0.0.1", port=settings.global_settings.webui_port)

            global _runtime  # noqa: PLW0603
            runtime = AppRuntime()
            with _runtime_lock:
                _runtime = runtime

            runtime.start(api_cfg, dashboard_cfg, enable_eventlog)
            asyncio.run(runtime.run())


if __name__ == "__main__":
    main()
