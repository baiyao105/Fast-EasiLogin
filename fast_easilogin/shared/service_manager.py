import contextlib

import servicemanager
import win32event
import win32service
import win32serviceutil


class WindowsServiceBase(win32serviceutil.ServiceFramework):
    _svc_name_ = "SeewoFastLoginService"
    _svc_display_name_ = "Seewo FastLogin Service"
    _svc_description_ = "Seewo FastLogin background service"

    def __init__(self, args: list[str]):
        super().__init__(args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)


class WindowsServiceManager:
    @staticmethod
    def install(
        service_name: str,
        module: str,
        klass: str,
        display_name: str | None = None,
        description: str | None = None,
        start_type: int = win32service.SERVICE_AUTO_START,
    ) -> None:
        svc_cls = f"{module}.{klass}"
        win32serviceutil.InstallService(
            pythonClassString=svc_cls,
            serviceName=service_name,
            displayName=display_name or service_name,
            startType=start_type,
            description=description or "",
        )

    @staticmethod
    def start(service_name: str) -> None:
        win32serviceutil.StartService(service_name)

    @staticmethod
    def remove(service_name: str) -> None:
        with contextlib.suppress(Exception):
            win32serviceutil.StopService(service_name)
        win32serviceutil.RemoveService(service_name)

    @staticmethod
    def set_autostart(service_name: str, auto_start: bool = True) -> None:
        scm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
        try:
            hsrv = win32service.OpenService(scm, service_name, win32service.SERVICE_ALL_ACCESS)
            try:
                win32service.ChangeServiceConfig(
                    hsrv,
                    win32service.SERVICE_NO_CHANGE,
                    win32service.SERVICE_AUTO_START if auto_start else win32service.SERVICE_DEMAND_START,
                    win32service.SERVICE_ERROR_NORMAL,
                    None,
                    None,
                    False,
                    None,
                    None,
                    None,
                    None,
                )
            finally:
                win32service.CloseServiceHandle(hsrv)
        finally:
            win32service.CloseServiceHandle(scm)
