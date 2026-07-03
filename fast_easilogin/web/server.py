import uvicorn

from .app import app


def run_web_server(port: int = 3000, log_level: str = "info") -> None:
    """启动 WebUI 服务"""
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level=log_level,
        server_header=False,
    )
    server = uvicorn.Server(config)
    server.run()
