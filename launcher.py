import asyncio
import contextlib
import importlib
import platform
import sys
import time
from datetime import UTC, datetime

import uvicorn
from loguru import logger

from proxy.server import start_mitm
from shared.basic_dir import LOGS_DIR, ensure_data_dirs
from shared.storage import load_appsettings_model


def _setup_logging() -> None:
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
    logger.add(str(logfile), level="INFO", encoding="utf-8", format=fmt, enqueue=True, backtrace=True, diagnose=False)
    files = sorted(logs_dir.glob("log_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in files[3:]:
        with contextlib.suppress(Exception):
            p.unlink()


def _setup_win_eventlog(enable: bool):
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


def main():
    s = load_appsettings_model()
    _setup_logging()
    report_event = _setup_win_eventlog(bool(getattr(s, "enable_eventlog", True)))
    _install_global_handlers(report_event)
    start_mitm(s.model_dump())
    base_port = int(s.port)
    listen_port = int(s.mitmproxy.listen_port)
    srv_port = base_port + 1 if listen_port == base_port else base_port

    def _run_once():
        uvicorn.run(
            "api.main:app",
            host="0.0.0.0",
            port=srv_port,
            server_header=False,
            access_log=False,
            log_config=None,
        )

    if bool(getattr(s, "auto_restart_on_crash", True)):
        delay = max(1, int(getattr(s, "restart_delay_seconds", 3)))
        while True:
            try:
                _run_once()
            except Exception as err:
                logger.exception("服务崩溃: {}", str(err))
                if report_event is not None:
                    with contextlib.suppress(Exception):
                        report_event(f"服务崩溃: {err}")
                time.sleep(delay)
                continue
            else:
                break
    else:
        _run_once()


if __name__ == "__main__":
    main()
