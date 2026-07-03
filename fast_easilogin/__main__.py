import win32event
import win32service

from fast_easilogin.app.runner import run, run_service
from fast_easilogin.app.utils import stop_server
from fast_easilogin.core.service_manager import WindowsServiceBase


def main():
    run()


class AppService(WindowsServiceBase):
    """Windows 服务"""

    _svc_name_ = "SeewoFastLoginService"
    _svc_display_name_ = "Seewo FastLogin Service"
    _svc_description_ = "Seewo FastLogin background service"

    def SvcStop(self):
        """响应停止请求"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        stop_server()
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        """启动服务"""
        run_service(log_level="INFO", access_log=False)


main()
