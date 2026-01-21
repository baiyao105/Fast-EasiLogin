from __future__ import annotations

import asyncio
import contextlib
import importlib
import logging
import os
import platform
import sys
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from shared.basic_dir import LOGS_DIR, ensure_data_dirs

_STATE: dict[str, Any] = {
    "server": None,
    "stop_event": threading.Event(),
    "mutex": None,
    "cfg": {
        "port": None,
        "access_log": False,
        "log_level": "INFO",
        "settings": None,
    },
}


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


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


def bridge_uvicorn_logs(level: str = "INFO", *, access_log: bool = False) -> None:
    logging.getLogger().handlers = [InterceptHandler()]
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = [InterceptHandler()]
        lg.propagate = False
        with contextlib.suppress(Exception):
            if access_log:
                lg.setLevel(getattr(logging, (level or "INFO").upper(), logging.INFO))
            else:
                lg.setLevel(logging.CRITICAL)


def setup_win_eventlog(enable: bool) -> Callable[[str], None] | None:
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


def install_global_handlers(report_event: Callable[[str], None] | None) -> None:
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

    try:
        loop = asyncio.get_event_loop()
    except Exception:
        loop = None

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


def ensure_single_instance(name: str = r"Local\SeewoFastLoginSingleInstance") -> bool:
    if platform.system() != "Windows":
        return True
    try:
        win32event = importlib.import_module("win32event")
        win32api = importlib.import_module("win32api")
        winerror = importlib.import_module("winerror")
    except Exception:
        return True
    h = win32event.CreateMutex(None, False, name)
    last_err = 0
    with contextlib.suppress(Exception):
        last_err = win32api.GetLastError()
    if last_err == getattr(winerror, "ERROR_ALREADY_EXISTS", 183):
        return False
    _STATE["mutex"] = h
    return True


def prepare_api_runtime(settings: Any, *, log_level: str = "INFO", access_log: bool = False) -> bool:
    ok = ensure_single_instance()
    if not ok:
        logger.warning("已有运行实例")
        return False
    _STATE["cfg"].update(
        {
            "settings": settings,
            "log_level": log_level,
            "access_log": bool(access_log),
        }
    )
    try:
        s = settings
        _STATE["cfg"]["port"] = int(s.Global.port)
    except Exception as err:
        logger.exception("初始化运行时失败: {}", str(err))
        return False
    bridge_uvicorn_logs(log_level, access_log=bool(access_log))
    return True


def get_api_port() -> int:
    cfg = _STATE.get("cfg") or {}
    return int(cfg.get("port") or 0)


def register_server(server: Any) -> None:
    _STATE["server"] = server


def stop(status: int = 0, *, force: bool = False) -> None:
    logger.info("程序退出")
    _STATE["stop_event"].set()
    srv = _STATE.get("server")
    if srv is not None:
        with contextlib.suppress(Exception):
            srv.should_exit = True
            srv.force_exit = True
    if force:
        os._exit(status)
