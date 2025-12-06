import sys
from pathlib import Path

from mitmproxy import http  # type: ignore

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from shared.storage import load_appsettings  # type: ignore

    PORT = int(load_appsettings().get("port", 24301))
except Exception:
    PORT = 24301


class SeewoHijack:
    def request(self, flow: http.HTTPFlow) -> None:
        host = (flow.request.host or "").lower()
        if host == "local.id.seewo.com":
            flow.request.host = "127.0.0.1"
            flow.request.port = PORT
            flow.request.scheme = "http"
            flow.request.headers["Host"] = "local.id.seewo.com"


addons = [SeewoHijack()]
