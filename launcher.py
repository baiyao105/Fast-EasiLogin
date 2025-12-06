import atexit
import shutil
import subprocess
from pathlib import Path

import uvicorn

from shared.storage import load_appsettings


def _start_mitm(appsettings):
    cfg = appsettings.get("mitmproxy") or {}
    if not bool(cfg.get("enable", True)):
        return None
    exe = shutil.which("mitmdump")
    if exe is None:
        return None
    listen_host = str(cfg.get("listen_host", "127.0.0.1"))
    listen_port = int(cfg.get("listen_port", 24300))
    script = cfg.get("script")
    if not script:
        script = str(Path(__file__).resolve().parent / "proxy" / "mitm_local_id.py")
    proc = subprocess.Popen(
        [exe, "-s", script, "--listen-host", listen_host, "--listen-port", str(listen_port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    atexit.register(lambda: proc.terminate())
    return proc


def main():
    appsettings = load_appsettings()
    _start_mitm(appsettings)
    port = int(appsettings.get("port", 24300))
    uvicorn.run("api.api:app", host="0.0.0.0", port=port, server_header=False)


if __name__ == "__main__":
    main()
