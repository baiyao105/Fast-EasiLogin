from collections.abc import Callable

import uvicorn

from fast_easilogin.api.main import app
from fast_easilogin.shared.store import load_appsettings_model

from .utils import install_global_handlers, set_server, setup_logging, setup_win_eventlog


def _init_environment(log_level: str) -> Callable[[str], None] | None:
    setup_logging(file_level=log_level)
    settings = load_appsettings_model()
    enable_eventlog = settings.Global.enable_eventlog
    report_event = setup_win_eventlog(enable_eventlog)
    install_global_handlers(report_event)
    return report_event


def run_service(log_level: str = "INFO", access_log: bool = False) -> None:
    _init_environment(log_level)
    port = load_appsettings_model().Global.port
    config = uvicorn.Config(
        app, host="127.0.0.1", port=port, server_header=False, access_log=access_log, log_config=None
    )
    server = uvicorn.Server(config)
    set_server(server)
    server.run()


def run_api(log_level: str = "INFO", access_log: bool = False) -> None:
    _init_environment(log_level)
    port = load_appsettings_model().Global.port
    uvicorn.run(app, host="127.0.0.1", port=port, server_header=False, access_log=access_log)
