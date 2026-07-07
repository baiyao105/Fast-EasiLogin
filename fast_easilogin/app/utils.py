from __future__ import annotations

import asyncio
import contextlib
import importlib
import logging
import platform
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from types import FrameType

from granian.server.embed import Server as GranianServer
from loguru import logger

from fast_easilogin.core.basic_dir import LOGS_DIR, ensure_data_dirs

_server: GranianServer | None = None


def stop_server() -> None:
    """停止服务"""
    srv = _server
    if srv is not None:
        srv.stop()
    logger.info("服务已停止")


def set_server(srv: GranianServer | None) -> None:
    global _server  # noqa: PLW0603
    _server = srv


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame: FrameType | None = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


class GranianAccessLogHandler(logging.Handler):
    """处理 Granian 的 access log 格式"""

    _FMT = '[{time}] {addr} - "{method} {path} {protocol}" {status} {dt_ms:.3f}'

    def emit(self, record: logging.LogRecord) -> None:
        msg = record.getMessage()
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        logger.opt(depth=1, exception=record.exc_info).log(level, msg)


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
        with contextlib.suppress(OSError):
            p.unlink()

    _setup_granian_logging()


def _setup_granian_logging() -> None:
    """将 Granian 的标准日志重定向到 loguru"""
    granian_logger = logging.getLogger("_granian")
    granian_logger.addHandler(InterceptHandler())
    granian_logger.setLevel(logging.WARNING)  # 只记录 WARNING 及以上级别

    access_logger = logging.getLogger("granian.access")
    access_logger.addHandler(GranianAccessLogHandler())
    access_logger.setLevel(logging.WARNING)  # 只记录 WARNING 及以上级别


def setup_win_eventlog(enable: bool) -> Callable[[str], None] | None:
    """配置 Windows 事件日志"""
    if (not enable) or platform.system() != "Windows":
        return None
    try:
        win32evtlog = importlib.import_module("win32evtlog")
        win32evtlogutil = importlib.import_module("win32evtlogutil")
    except ImportError:
        return None

    app_name = "fast_easilogin"
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


def install_global_handlers(report_event: Callable[[str], None] | None = None) -> None:
    def _excepthook(exc_type, value, tb):
        if exc_type is None or exc_type is KeyboardInterrupt:
            return
        try:
            logger.opt(exception=(exc_type, value, tb)).error("未捕获的异常: {}", value)
        finally:
            if report_event is not None:
                with contextlib.suppress(Exception):
                    report_event(f"未捕获的异常: {value}")

    sys.excepthook = _excepthook

    loop = _get_event_loop()
    if loop is not None:

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


def _get_event_loop():
    try:
        return asyncio.get_event_loop()
    except Exception:
        return None
