import contextlib
import sys
from datetime import UTC, datetime

from loguru import logger

from fast_easilogin.core.basic_dir import LOGS_DIR, ensure_data_dirs
from fast_easilogin.core.constants import APP_NAME


def setup_logging(log_level: str = "INFO") -> None:
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
        level=(log_level or "INFO"),
        encoding="utf-8",
        format=fmt,
        enqueue=True,
        backtrace=True,
        diagnose=False,
    )

    # 只保留最近 3 个日志文件
    files = sorted(logs_dir.glob("log_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in files[3:]:
        with contextlib.suppress(OSError):
            p.unlink()


def bootstrap(log_level: str = "INFO") -> None:
    """初始化"""
    logger.info("Initializing {}...", APP_NAME)
    setup_logging(log_level)
    ensure_data_dirs()
    logger.success("Bootstrap completed")
