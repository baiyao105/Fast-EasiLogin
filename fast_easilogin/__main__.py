import win32event
import win32service

from fast_easilogin.runtime.mode import parse_mode
from fast_easilogin.runtime.service_runner import run_api, run_service
from fast_easilogin.runtime.utils import stop_server
from fast_easilogin.shared.service_manager import WindowsServiceBase, WindowsServiceManager


def main(argv: list[str] | None = None):
    mode = parse_mode(argv)
    if mode.services == "install":
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
    if mode.services == "uninstall":
        WindowsServiceManager.remove("SeewoFastLoginService")
        return
    run_api(log_level=mode.log_level, access_log=mode.access_log)


class AppService(WindowsServiceBase):
    _svc_name_ = "SeewoFastLoginService"
    _svc_display_name_ = "Seewo FastLogin Service"
    _svc_description_ = "Seewo FastLogin background service"

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        stop_server()
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        run_service(log_level="INFO", access_log=False)


main()
