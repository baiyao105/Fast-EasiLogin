import asyncio
import atexit
import contextlib
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any

from loguru import logger

from shared.store.config import load_appsettings


def _resolve_app_port() -> int:
    s = load_appsettings()
    g = s.get("Global") or {}
    base = int(g.get("port", 24300))
    m = s.get("mitmproxy") or {}
    listen = int(m.get("listen_port", base))
    return base + 1 if listen == base else base


def _get_repo_root() -> Path:
    try:
        return Path(__file__).resolve().parent.parent
    except Exception:
        return Path.cwd()


def _script_text(port: int) -> str:
    return f"""
from mitmproxy import http

PORT = {port}

class SeewoHijack:
    def request(self, flow: http.HTTPFlow) -> None:
        host = (flow.request.host or "").lower()
        if host == "local.id.seewo.com":
            flow.request.host = "127.0.0.1"
            flow.request.port = PORT
            flow.request.scheme = "http"
            flow.request.headers["Host"] = "local.id.seewo.com"

addons = [SeewoHijack()]
"""


def _start_mitmdump(cfg: dict[str, Any]):
    exe = shutil.which("mitmdump")
    if exe is None:
        return None
    listen_host = str(cfg.get("listen_host", "127.0.0.1"))
    listen_port = int(cfg.get("listen_port", 24300))
    script = cfg.get("script")
    if not script:
        repo_script = _get_repo_root() / "proxy" / "mitm_local_id.py"
        if repo_script.exists():
            script = str(repo_script)
        else:
            port = _resolve_app_port()
            with tempfile.NamedTemporaryFile(prefix="seewo_mitm_", suffix=".py", delete=False) as tmp:
                tmp.write(_script_text(port).encode("utf-8"))
                tmp.flush()
                script = tmp.name

    proc = subprocess.Popen(
        [exe, "-s", script, "--listen-host", listen_host, "--listen-port", str(listen_port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    atexit.register(lambda: proc.terminate())
    logger.success("mitmproxy启动成功: mode=mitmdump listen={}:{}", listen_host, listen_port)
    return proc


def _start_inprocess(cfg: dict[str, Any]):
    try:
        from mitmproxy import http, options  # noqa: PLC0415
    except Exception:
        return None

    listen_host = str(cfg.get("listen_host", "127.0.0.1"))
    listen_port = int(cfg.get("listen_port", 24300))
    app_port = _resolve_app_port()

    class SeewoHijack:
        def request(self, flow: http.HTTPFlow) -> None:
            host = (flow.request.host or "").lower()
            if host == "local.id.seewo.com":
                flow.request.host = "127.0.0.1"
                flow.request.port = app_port
                flow.request.scheme = "http"
                flow.request.headers["Host"] = "local.id.seewo.com"

    opts = options.Options(listen_host=listen_host, listen_port=listen_port)

    def _run():
        async def _main():
            from mitmproxy.tools.dump import DumpMaster  # noqa: PLC0415

            m = DumpMaster(opts, with_termlog=False, with_dumper=False)
            m.addons.add(SeewoHijack())
            await m.run()

        with contextlib.suppress(Exception):
            asyncio.run(_main())

    th = threading.Thread(target=_run, name="mitmproxy-thread", daemon=True)
    th.start()
    logger.success("mitmproxy启动成功: mode=inprocess listen={}:{} app_port={}", listen_host, listen_port, app_port)
    return th


def start_mitm(appsettings: dict[str, Any]):
    cfg = appsettings.get("mitmproxy") or {}
    if not bool(cfg.get("enable", True)):
        return None
    inst = _start_inprocess(cfg)
    if inst is not None:
        return inst
    return _start_mitmdump(cfg)
