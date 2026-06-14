import asyncio
import os
from typing import Any

import httpx
from loguru import logger

from .constants import HTTP_SERVER_ERROR
from .errors import RequestFailedError


def _compute_limits() -> httpx.Limits:
    cpu = max(1, int(os.cpu_count() or 1))
    max_conns = min(max(100, cpu * 200), 2000)
    keepalive = max(50, max_conns // 2)
    return httpx.Limits(max_keepalive_connections=keepalive, max_connections=max_conns)


CLIENT_TIMEOUT = httpx.Timeout(connect=1.0, read=3.0, write=3.0, pool=10.0)
CLIENT_LIMITS = _compute_limits()
CLIENT_HTTP2 = True


class HttpClientManager:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._rc = 0

    async def init(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=CLIENT_TIMEOUT, limits=CLIENT_LIMITS, http2=CLIENT_HTTP2)
        self._rc += 1

    async def close(self) -> None:
        self._rc = max(0, self._rc - 1)
        if self._rc == 0 and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def request_with_retry(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        max_attempts: int = 2,
        backoff_base: float = 0.2,
    ) -> httpx.Response:
        client = self._client
        if client is None:
            raise RuntimeError("HttpClientManager 未初始化, 请先调用 init()")
        last_err: Exception | None = None
        for attempt in range(max_attempts):
            try:
                if method == "GET":
                    r = await client.get(url, headers=headers, cookies=cookies)
                else:
                    r = await client.post(url, headers=headers, cookies=cookies, json=json)
                if r.status_code >= HTTP_SERVER_ERROR:
                    msg = f"服务端错误: url={url} status={r.status_code}"
                    logger.error("[第{}次] {}", attempt + 1, msg)
                    last_err = RequestFailedError(msg)
                    await asyncio.sleep(backoff_base * (2**attempt))
                    continue
            except httpx.TimeoutException as e:
                logger.error("[第{}次] 超时: url={} err={}", attempt + 1, url, e)
                last_err = e
                await asyncio.sleep(backoff_base * (2**attempt))
                continue
            except httpx.HTTPError as e:
                logger.error("[第{}次] HTTP错误: url={} err={}", attempt + 1, url, e)
                last_err = e
                await asyncio.sleep(backoff_base * (2**attempt))
                continue
            else:
                return r
        raise RequestFailedError(f"请求失败, 已达最大重试次数{max_attempts}: url={url}") from last_err


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
    max_attempts: int = 2,
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
