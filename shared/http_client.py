import asyncio
import os
import threading
import time
from typing import Any

import httpx

from .constants import FAIL_THRESHOLD, HTTP_SERVER_ERROR, RESET_TIMEOUT
from .errors import CircuitOpenError, RequestFailedError


def _compute_limits() -> httpx.Limits:
    cpu = max(1, int(os.cpu_count() or 1))
    max_conns = max(100, cpu * 200)
    keepalive = max(20, cpu * 50)
    return httpx.Limits(max_keepalive_connections=keepalive, max_connections=max_conns)


CLIENT_TIMEOUT = httpx.Timeout(connect=1.0, read=3.0, write=3.0, pool=10.0)
CLIENT_LIMITS = _compute_limits()
CLIENT_HTTP2 = True


class HttpClientManager:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._rc = 0
        self._opened_at: float | None = None
        self._breaker: dict[str, dict[str, Any]] = {}
        self._br_lock = threading.Lock()

    async def init(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=CLIENT_TIMEOUT, limits=CLIENT_LIMITS, http2=CLIENT_HTTP2)
            self._opened_at = time.time()
        self._rc += 1

    async def close(self) -> None:
        self._rc = max(0, self._rc - 1)
        if self._rc == 0 and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _host_from_url(self, url: str) -> str:
        try:
            return url.split("/")[2]
        except Exception:
            return ""

    def _breaker_state(self, host: str) -> dict[str, Any]:
        with self._br_lock:
            st = self._breaker.get(host)
            if st is None:
                st = {"fail": 0, "opened_at": 0.0, "open": False, "half": False}
                self._breaker[host] = st
            return st

    def _should_block(self, host: str) -> bool:
        st = self._breaker_state(host)
        if st["open"]:
            elapsed = time.time() - float(st["opened_at"] or 0.0)
            if elapsed < RESET_TIMEOUT:
                return True
            with self._br_lock:
                st["open"] = False
                st["half"] = True
                self._breaker[host] = st
        return False

    def _record_success(self, host: str) -> None:
        with self._br_lock:
            self._breaker[host] = {"fail": 0, "opened_at": 0.0, "open": False, "half": False}

    def _record_failure(self, host: str) -> None:
        st = self._breaker_state(host)
        with self._br_lock:
            st["fail"] = int(st["fail"]) + 1
            if st["fail"] >= FAIL_THRESHOLD:
                st["open"] = True
                st["opened_at"] = time.time()
                st["half"] = False
            self._breaker[host] = st

    async def request_with_retry(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        max_attempts: int = 3,
        backoff_base: float = 0.2,
    ) -> httpx.Response:
        host = self._host_from_url(url)
        client = self._client or httpx.AsyncClient(timeout=CLIENT_TIMEOUT, limits=CLIENT_LIMITS, http2=CLIENT_HTTP2)
        for attempt in range(max_attempts):
            if self._should_block(host):
                raise CircuitOpenError()
            try:
                if method == "GET":
                    r = await client.get(url, headers=headers, cookies=cookies)
                else:
                    r = await client.post(url, headers=headers, cookies=cookies, json=json)
                if r.status_code >= HTTP_SERVER_ERROR:
                    self._record_failure(host)
                    await asyncio.sleep(backoff_base * (2**attempt))
                    continue
            except Exception:
                self._record_failure(host)
                await asyncio.sleep(backoff_base * (2**attempt))
                continue
            else:
                self._record_success(host)
                return r
        raise RequestFailedError()


_HTTP_MANAGER = HttpClientManager()


async def init_http_client() -> None:
    await _HTTP_MANAGER.init()


async def close_http_client() -> None:
    await _HTTP_MANAGER.close()


async def request_with_retry(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    cookies: dict[str, str] | None = None,
    json: dict[str, Any] | None = None,
    max_attempts: int = 3,
    backoff_base: float = 0.2,
):
    return await _HTTP_MANAGER.request_with_retry(
        method,
        url,
        headers=headers,
        cookies=cookies,
        json=json,
        max_attempts=max_attempts,
        backoff_base=backoff_base,
    )
