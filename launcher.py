import contextlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from loguru import logger

from proxy.server import start_mitm
from shared.storage import ensure_data_dir, load_appsettings


def _setup_logging() -> None:
    ensure_data_dir()
    logs_dir = Path(__file__).resolve().parent / "data" / "Logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(sys.stdout, level="TRACE", enqueue=True, backtrace=True, diagnose=False)
    ts = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d-%H-%M")
    logfile = logs_dir / f"log_{ts}.log"
    logger.add(str(logfile), level="INFO", encoding="utf-8", enqueue=True, backtrace=True, diagnose=False)
    files = sorted(logs_dir.glob("log_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in files[3:]:
        with contextlib.suppress(Exception):
            p.unlink()


def main():
    appsettings = load_appsettings()
    _setup_logging()
    start_mitm(appsettings)
    base_port = int(appsettings.get("port", 24300))
    mitm = appsettings.get("mitmproxy") or {}
    listen_port = int(mitm.get("listen_port", base_port))
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
