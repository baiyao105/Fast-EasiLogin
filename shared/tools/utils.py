from __future__ import annotations

import contextlib
import importlib
import logging
import os
import platform
import threading
from typing import Any, cast

import uvicorn
from loguru import logger

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


def _bridge_uvicorn_logs(level: str = "INFO") -> None:
    logging.getLogger().handlers = [InterceptHandler()]
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = [InterceptHandler()]
        lg.propagate = False
        with contextlib.suppress(Exception):
            lg.setLevel(getattr(logging, (level or "INFO").upper(), logging.INFO))


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


def init_runtime(settings: Any, *, log_level: str = "INFO", access_log: bool = False) -> bool:
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
        _proxy_server = importlib.import_module("proxy.server")
        s = settings
        _proxy_server.start_mitm(s.model_dump())
        base_port = int(s.Global.port)
        listen_port = int(s.mitmproxy.listen_port)
        srv_port = base_port + 1 if listen_port == base_port else base_port
        _STATE["cfg"]["port"] = srv_port
    except Exception as err:
        logger.exception("初始化运行时失败: {}", str(err))
        return False
    _bridge_uvicorn_logs(log_level)
    return True


def start() -> None:
    cfg = _STATE.get("cfg") or {}
    port = int(cfg.get("port") or 0)
    if not port:
        logger.error("未配置端口")
        return
    access_log = bool(cfg.get("access_log"))
    server = uvicorn.Server(
        uvicorn.Config(
            "api.main:app",
            host="0.0.0.0",
            port=port,
            server_header=False,
            access_log=access_log,
            log_config=None,
        )
    )
    with contextlib.suppress(Exception):
        cast(Any, server).install_signal_handlers = False
    _STATE["server"] = server
    try:
        server.run()
    finally:
        _STATE["server"] = None


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
