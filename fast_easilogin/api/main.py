from __future__ import annotations

import json
import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from fast_easilogin.api.gateway.router import router
from fast_easilogin.core.constants import ALLOWED_ORIGINS
from fast_easilogin.core.errors import LoginFailedError, NetworkError
from fast_easilogin.core.lifespan import lifespan
from fast_easilogin.core.services import Services

# 敏感字段在捕获日志中打码，避免明文落盘
_REDACT_KEYS = {
    "password",
    "pt_token",
    "token",
    "secret",
    "authorization",
    "cookie",
    "x-auth-token",
}


def _redact_value(key: str, value: Any) -> Any:
    lowered = key.lower()
    if any(s in lowered for s in _REDACT_KEYS):
        if isinstance(value, str) and value:
            return f"***{value[-4:]}" if len(value) > 4 else "***"
        return "***"
    return value


def _redact_headers(headers: dict[str, str]) -> dict[str, str]:
    return {k: _redact_value(k, v) for k, v in headers.items()}


def _redact_body(body: Any) -> Any:
    if isinstance(body, dict):
        return {
            k: _redact_value(k, _redact_body(v)) if not isinstance(v, (dict, list)) else _redact_body(v)
            for k, v in body.items()
        }
    if isinstance(body, list):
        return [_redact_body(i) for i in body]
    return body


def create_app(services: Services | None = None) -> FastAPI:
    app = FastAPI(title="FastLogin", lifespan=lifespan)
    if services is not None:
        app.state.services = services

    @app.exception_handler(LoginFailedError)
    async def login_failed_handler(request: Request, exc: LoginFailedError):
        return JSONResponse(status_code=401, content={"message": str(exc), "statusCode": "401"})

    @app.exception_handler(NetworkError)
    async def network_error_handler(request: Request, exc: NetworkError):
        return JSONResponse(status_code=504, content={"message": str(exc), "statusCode": "504"})

    @app.middleware("http")
    async def capture_gateway_requests(request: Request, call_next):
        """捕获客户端打到网关（非 WebUI）的请求，便于逆向协议/加功能。"""
        started = time.perf_counter()
        body_text: str | None = None
        body_parsed: Any = None
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            raw = await request.body()
            if raw:
                try:
                    body_text = raw.decode("utf-8", errors="replace")
                    body_parsed = json.loads(body_text)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    body_text = body_text[:2000] if body_text else None
                    body_parsed = None

        status_code = 500
        error: str | None = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            svc = getattr(request.app.state, "services", None)
            store = getattr(svc, "api_capture", None) if svc else None
            if store is not None and store.enabled:
                duration_ms = (time.perf_counter() - started) * 1000
                try:
                    store.add(
                        method=request.method,
                        path=request.url.path,
                        query=str(request.url.query or ""),
                        client=request.client.host if request.client else "",
                        headers=_redact_headers(dict(request.headers)),
                        body=_redact_body(body_parsed),
                        body_raw=body_text[:2000] if body_text else None,
                        status_code=status_code,
                        duration_ms=duration_ms,
                        error=error,
                    )
                except Exception:
                    logger.exception("API 捕获写入失败")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.include_router(router)

    return app
