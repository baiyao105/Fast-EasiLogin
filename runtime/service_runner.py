import contextlib
import time
from typing import Any, cast

import uvicorn
from loguru import logger

from shared.store.config import load_appsettings_model

from .utils import (
    get_api_port,
    install_global_handlers,
    prepare_api_runtime,
    register_server,
    setup_logging,
    setup_win_eventlog,
)


def run_service(log_level: str = "INFO", access_log: bool = False, *, with_webui: bool = True) -> None:
    s = load_appsettings_model()
    setup_logging(file_level=(log_level or "INFO"))
    enable_eventlog = bool(getattr(s, "Global", None) and s.Global.enable_eventlog)
    report_event = setup_win_eventlog(enable_eventlog)
    install_global_handlers(report_event)

    if not prepare_api_runtime(s, log_level=(log_level or "INFO"), access_log=bool(access_log)):
        return

    auto_restart = bool(getattr(s, "Global", None) and s.Global.auto_restart_on_crash)
    if auto_restart:
        delay = max(1, int(s.Global.restart_delay_seconds))
        while True:
            try:
                port = get_api_port()
                if not port:
                    port = int(s.Global.port)
                server = uvicorn.Server(
                    uvicorn.Config(
                        "api.main:app",
                        host="0.0.0.0",
                        port=port,
                        server_header=False,
                        access_log=bool(access_log),
                        log_config=None,
                    )
                )
                register_server(server)
                server.run()
            except Exception as err:
                logger.exception("服务异常退出: {}", str(err))
                if report_event is not None:
                    with contextlib.suppress(Exception):
                        report_event(f"服务异常退出: {err}")
                logger.info("将在 {} 秒后重启...", delay)
                time.sleep(delay)
                continue
            else:
                break
    else:
        port = get_api_port()
        if not port:
            port = int(s.Global.port)
        server = uvicorn.Server(
            uvicorn.Config(
                "api.main:app",
                host="0.0.0.0",
                port=port,
                server_header=False,
                access_log=bool(access_log),
                log_config=None,
            )
        )
        with contextlib.suppress(Exception):
            cast(Any, server).install_signal_handlers = False
        register_server(server)

        server.run()


def run_api(log_level: str = "INFO", access_log: bool = False) -> None:
    run_service(log_level=log_level, access_log=access_log, with_webui=False)
