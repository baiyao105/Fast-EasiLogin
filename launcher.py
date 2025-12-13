import argparse
import asyncio
import contextlib
import importlib
import platform
import sys
import time
from datetime import UTC, datetime

import win32event
import win32service
from loguru import logger

from shared.basic_dir import LOGS_DIR, ensure_data_dirs
from shared.config.config import load_appsettings_model
from shared.service_manager import WindowsServiceBase, WindowsServiceManager
from shared.tools import utils as tools_utils
from shared.tools.decorators import setup_signal_handlers


def _setup_logging(file_level: str = "INFO") -> None:
    ensure_data_dirs()
    logs_dir = LOGS_DIR
    logs_dir.mkdir(parents=True, exist_ok=True)
    fmt = (
        "<blue>{time:YYYY-MM-DD HH:mm:ss}</blue> | "
        "<level>{level: <7}</level> | "
        "<magenta>{name}</magenta>:<cyan>{function}</cyan> | "
        "{message}"
    )
    logger.remove()
    logger.add(sys.stdout, level="TRACE", format=fmt, enqueue=True, backtrace=True, diagnose=False)
    ts = datetime.now(UTC).astimezone().strftime("%Y-%m-%d-%H-%M")
    logfile = logs_dir / f"log_{ts}.log"
    logger.add(
        str(logfile),
        level=(file_level or "INFO"),
        encoding="utf-8",
        format=fmt,
        enqueue=True,
        backtrace=True,
        diagnose=False,
    )

    files = sorted(logs_dir.glob("log_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in files[3:]:
        with contextlib.suppress(Exception):
            p.unlink()


def _setup_win_eventlog(enable: bool):
    """配置 Windows 事件日志"""
    if (not enable) or platform.system() != "Windows":
        return None
    try:
        win32evtlog = importlib.import_module("win32evtlog")
        win32evtlogutil = importlib.import_module("win32evtlogutil")
    except Exception:
        return None

    app_name = "Fast-EasiLogin"
    with contextlib.suppress(Exception):
        win32evtlogutil.AddSourceToRegistry(app_name)

    def _report_event(text: str):
        et = win32evtlog.EVENTLOG_ERROR_TYPE
        with contextlib.suppress(Exception):
            win32evtlogutil.ReportEvent(app_name, 1000, 0, et, [text])

    def _sink(msg):
        rec = msg.record
        lvl = rec["level"].name
        text = msg.render()
        if lvl in ("ERROR", "CRITICAL") or rec.get("exception"):
            _report_event(text)

    with contextlib.suppress(Exception):
        logger.add(_sink, level="ERROR", enqueue=True)
    return _report_event


def _install_global_handlers(report_event):
    @logger.catch
    def _excepthook(exctype, value, tb):
        try:
            logger.exception("未捕获的异常: {}", str(value))
        finally:
            if report_event is not None:
                with contextlib.suppress(Exception):
                    report_event(f"未捕获的异常: {value}")

    sys.excepthook = _excepthook

    try:
        loop = asyncio.get_event_loop()
    except Exception:
        loop = None

    if loop is not None:

        @logger.catch
        def _loop_handler(_loop, context):
            err = context.get("exception")
            msg = context.get("message") or ""
            if err is not None:
                logger.exception("异步中未捕获的异常: {}", str(err))
                if report_event is not None:
                    with contextlib.suppress(Exception):
                        report_event(f"异步中未捕获的异常: {err}")
            else:
                logger.error("异步错误: {}", str(msg))
                if report_event is not None:
                    with contextlib.suppress(Exception):
                        report_event(f"异步错误: {msg}")

        with contextlib.suppress(Exception):
            loop.set_exception_handler(_loop_handler)


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--services", choices=["install", "uninstall"], default=None)
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--log-access", choices=["on", "off"], default="off")
    args = parser.parse_args(argv)

    s = load_appsettings_model()
    _setup_logging(file_level=(args.log_level or "INFO"))
    enable_eventlog = bool(getattr(s, "Global", None) and s.Global.enable_eventlog)
    report_event = _setup_win_eventlog(enable_eventlog)
    _install_global_handlers(report_event)
    if args.services == "install":
        WindowsServiceManager.install(
            service_name="SeewoFastLoginService",
            module="launcher",
            klass="AppService",
            display_name="Seewo FastLogin Service",
            description="Seewo FastLogin background service",
        )
        with contextlib.suppress(Exception):
            WindowsServiceManager.set_autostart("SeewoFastLoginService", True)
        with contextlib.suppress(Exception):
            WindowsServiceManager.start("SeewoFastLoginService")
        return
    if args.services == "uninstall":
        WindowsServiceManager.remove("SeewoFastLoginService")
        return

    def _on_signal():
        tools_utils.stop()

    setup_signal_handlers(on_stop=_on_signal)
    if not tools_utils.init_runtime(s, log_level=(args.log_level or "INFO"), access_log=(args.log_access == "on")):
        return
    stop_event = tools_utils._STATE["stop_event"]

    def _run_once():
        if stop_event.is_set():
            return
        tools_utils.start()

    auto_restart = bool(getattr(s, "Global", None) and s.Global.auto_restart_on_crash)

    if auto_restart:
        delay = max(1, int(s.Global.restart_delay_seconds))
        while not stop_event.is_set():
            try:
                _run_once()
            except Exception as err:
                logger.exception("服务异常退出: {}", str(err))
                if report_event is not None:
                    with contextlib.suppress(Exception):
                        report_event(f"服务异常退出: {err}")

                if stop_event.is_set():
                    break

                logger.info("将在 {} 秒后重启...", delay)
                time.sleep(delay)
                continue
            else:
                break
    else:
        _run_once()


class AppService(WindowsServiceBase):
    _svc_name_ = "SeewoFastLoginService"
    _svc_display_name_ = "Seewo FastLogin Service"
    _svc_description_ = "Seewo FastLogin background service"

    def SvcStop(self):
        """服务停止回调"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        tools_utils.stop()
        win32event.SetEvent(getattr(self, "hWaitStop", win32event.CreateEvent(None, 0, 0, None)))

    def SvcDoRun(self):
        """服务运行主逻辑"""
        s = load_appsettings_model()
        _setup_logging(file_level="INFO")

        enable_eventlog = bool(getattr(s, "Global", None) and s.Global.enable_eventlog)
        report_event = _setup_win_eventlog(enable_eventlog)
        _install_global_handlers(report_event)

        if not tools_utils.init_runtime(s, log_level="INFO", access_log=False):
            return

        tools_utils.start()


if __name__ == "__main__":
    main()
