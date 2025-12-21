import asyncio
import contextlib
import ctypes
import importlib
import platform
import signal
import sys
from datetime import UTC, datetime

from loguru import logger

from shared.basic_dir import LOGS_DIR, ensure_data_dirs


def setup_logging(file_level: str = "INFO") -> None:
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


def setup_win_eventlog(enable: bool):
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
        try:
            rec = msg.record
        except Exception:
            with contextlib.suppress(Exception):
                _report_event(str(msg))
            return
        lvl_obj = rec.get("level")
        lvl_no = getattr(lvl_obj, "no", logger.level("INFO").no)
        text = rec.get("message", "")
        exc = rec.get("exception")
        if exc:
            with contextlib.suppress(Exception):
                typ = getattr(exc, "type", None)
                val = getattr(exc, "value", None)
                if typ or val:
                    text = f"{text}\n{getattr(typ, '__name__', typ)}: {val}"
        if lvl_no >= logger.level("ERROR").no:
            _report_event(text)

    with contextlib.suppress(Exception):
        logger.add(_sink, level="ERROR", enqueue=True)
    return _report_event


def install_global_handlers(report_event):
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


def setup_signal_handlers(on_stop=None):
    def _handle_signal(signum, _frame):
        with contextlib.suppress(Exception):
            logger.warning("收到退出信号: {}", signum)
        try:
            if callable(on_stop):
                on_stop()
        except Exception:
            pass

    for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        sig = getattr(signal, name, None)
        if sig is not None:
            try:
                signal.signal(sig, _handle_signal)
                logger.trace("注册信号处理器: {}", name)
            except Exception as e:
                logger.error("注册 {} 失败: {}", name, e)

    if platform.system() == "Windows":
        with contextlib.suppress(Exception):
            DWORD = ctypes.c_ulong
            BOOL = ctypes.c_int
            HandlerRoutine = ctypes.WINFUNCTYPE(BOOL, DWORD)

            def _console_handler(ctrl_type):
                try:
                    if callable(on_stop):
                        on_stop()
                except Exception:
                    pass
                return 1

            ctypes.windll.kernel32.SetConsoleCtrlHandler(HandlerRoutine(_console_handler), True)
            logger.trace("注册控制台处理器: SetConsoleCtrlHandler")


def install_signal_handlers(on_stop=None):
    setup_signal_handlers(on_stop=on_stop)
