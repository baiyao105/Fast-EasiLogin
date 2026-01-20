from mitmproxy import http

from shared.store.config import load_appsettings

PORT = int((load_appsettings().get("Global") or {}).get("port", 24301))


class SeewoHijack:
    def request(self, flow: http.HTTPFlow) -> None:
        host = (flow.request.host or "").lower()
        if host == "local.id.seewo.com":
            flow.request.host = "127.0.0.1"
            flow.request.port = PORT
            flow.request.scheme = "http"
            flow.request.headers["Host"] = "local.id.seewo.com"


addons = [SeewoHijack()]
