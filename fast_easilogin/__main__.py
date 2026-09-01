import sys
import threading

from fast_easilogin.app.runner import run

_runtime = None
_runtime_lock = threading.Lock()


def main():
    run()


if sys.platform == "win32":
    import win32event
    import win32service

    from fast_easilogin.core.service_manager import WindowsServiceBase

    class AppService(WindowsServiceBase):
        """Windows 服务"""

        _svc_name_ = "SeewoFastLoginService"
        _svc_display_name_ = "Seewo FastLogin Service"
        _svc_description_ = "Seewo FastLogin background service"

        def SvcStop(self):
            """停止"""
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            with _runtime_lock:
                if _runtime is not None:
                    _runtime.stop()
            win32event.SetEvent(self.hWaitStop)

        def SvcDoRun(self):
            """启动"""
            import asyncio

            from fast_easilogin.app.bootstrap import bootstrap
            from fast_easilogin.app.runtime import AppRuntime, ServerConfig
            from fast_easilogin.app.utils import install_global_handlers, setup_win_eventlog
            from fast_easilogin.storage import load_settings_sync

            bootstrap(log_level="INFO")
            settings = load_settings_sync()
            enable_eventlog = settings.global_settings.enable_eventlog
            report_event = setup_win_eventlog(enable_eventlog)
            install_global_handlers(report_event)

            global _runtime  # noqa: PLW0603
            runtime = AppRuntime()
            with _runtime_lock:
                _runtime = runtime

            api_cfg = ServerConfig(host="0.0.0.0", port=settings.global_settings.port)
            dashboard_cfg = ServerConfig(host="127.0.0.1", port=settings.global_settings.webui_port)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(runtime.start(api_cfg, dashboard_cfg))
                loop.run_until_complete(runtime.run())
            finally:
                loop.run_until_complete(runtime.shutdown())
                loop.close()
                with _runtime_lock:
                    _runtime = None


if __name__ == "__main__":
    main()
