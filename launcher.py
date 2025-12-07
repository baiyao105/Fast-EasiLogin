import contextlib
import sys
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


def main():
    s = load_appsettings_model()
    _setup_logging()
    start_mitm(s.model_dump())
    base_port = int(s.port)
    listen_port = int(s.mitmproxy.listen_port)
    srv_port = base_port + 1 if listen_port == base_port else base_port
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=srv_port,
        server_header=False,
        access_log=False,
        log_config=None,
    )


if __name__ == "__main__":
    main()
