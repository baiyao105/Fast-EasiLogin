from __future__ import annotations

import contextlib
import ctypes
import platform
import signal

from loguru import logger


def deprecated_field(name: str, *, replacement: str | None = None):
    def _cls_decorator(cls: type) -> type:
        info = getattr(cls, "_deprecated_fields", {})
        info[name] = {"replacement": replacement}
        cls._deprecated_fields = info
        return cls

    return _cls_decorator


def setup_signal_handlers(on_stop=None):
    """退出信号处理器"""

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
