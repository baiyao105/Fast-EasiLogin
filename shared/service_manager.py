from __future__ import annotations

import contextlib
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, cast

import servicemanager
import win32event
import win32service
import win32serviceutil


class WindowsServiceProtocol(ABC):
    @property
    @abstractmethod
    def service_name(self) -> str: ...

    @property
    @abstractmethod
    def display_name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @abstractmethod
    def on_start(self) -> None: ...

    @abstractmethod
    def on_stop(self) -> None: ...


_CALLBACKS: dict[str, Callable[[], Any] | None] = {"start": None, "stop": None}


class WindowsServiceBase(win32serviceutil.ServiceFramework):
    _svc_name_ = "SeewoFastLoginService"
    _svc_display_name_ = "Seewo FastLogin Service"
    _svc_description_ = "Seewo FastLogin background service"

    def __init__(self, args):
        super().__init__(args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self._on_start = _CALLBACKS["start"]
        self._on_stop = _CALLBACKS["stop"]

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        if self._on_stop:
            with contextlib.suppress(Exception):
                self._on_stop()
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        if self._on_start:
            with contextlib.suppress(Exception):
                self._on_start()
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

    @classmethod
    def configure(
        cls,
        svc_name: str,
        display_name: str | None = None,
        description: str | None = None,
        on_start: Callable[[], Any] | None = None,
        on_stop: Callable[[], Any] | None = None,
    ) -> type[WindowsServiceBase]:
        cls._svc_name_ = svc_name
        cls._svc_display_name_ = display_name or svc_name
        cls._svc_description_ = description or ""
        _CALLBACKS.update({"start": on_start, "stop": on_stop})
        return cls


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
    def remove(service_name: str) -> None:
        with contextlib.suppress(Exception):
            win32serviceutil.StopService(service_name)
        win32serviceutil.RemoveService(service_name)

    @staticmethod
    def exists(service_name: str) -> bool:
        try:
            win32serviceutil.QueryServiceStatus(service_name)
        except Exception:
            return False
        else:
            return True

    @staticmethod
    def start(service_name: str) -> None:
        win32serviceutil.StartService(service_name)

    @staticmethod
    def stop(service_name: str) -> None:
        win32serviceutil.StopService(service_name)

    @staticmethod
    def restart(service_name: str) -> None:
        try:
            win32serviceutil.RestartService(service_name)
        except Exception:
            win32serviceutil.StopService(service_name)
            win32serviceutil.StartService(service_name)

    @staticmethod
    def status(service_name: str) -> int | None:
        try:
            st = win32serviceutil.QueryServiceStatus(service_name)
            return cast(int, st[1])
        except Exception:
            return None

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
