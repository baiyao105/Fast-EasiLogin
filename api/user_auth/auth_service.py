import asyncio
import hashlib
import json
import os
import random
import secrets
import threading
import time
from typing import Any

import httpx
from fastapi import HTTPException
from loguru import logger

from shared.storage import get_cache


def _compute_limits() -> httpx.Limits:
    cpu = max(1, int(os.cpu_count() or 1))
    max_conns = max(100, cpu * 200)
    keepalive = max(20, cpu * 50)
    return httpx.Limits(max_keepalive_connections=keepalive, max_connections=max_conns)


CLIENT_TIMEOUT = httpx.Timeout(connect=1.0, read=3.0, write=3.0, pool=10.0)
CLIENT_LIMITS = _compute_limits()
CLIENT_HTTP2 = True

_CLIENT: httpx.AsyncClient | None = None
_CLIENT_RC = 0
_CLIENT_OPENED_AT: float | None = None
LOGIN_TTL = 120.0
USERINFO_TTL = 300.0
_BREAKER: dict[str, dict[str, Any]] = {}
_BR_LOCK = threading.Lock()
TOKEN_INVALID_CODE = 40105
_FAIL_THRESHOLD = 3
_RESET_TIMEOUT = 10.0


def _get_client() -> httpx.AsyncClient:
    global _CLIENT, _CLIENT_OPENED_AT
    if _CLIENT is None:
        _CLIENT = httpx.AsyncClient(timeout=CLIENT_TIMEOUT, limits=CLIENT_LIMITS, http2=CLIENT_HTTP2)
        _CLIENT_OPENED_AT = time.time()
    return _CLIENT


async def init_http_client() -> None:
    global _CLIENT_RC
    _get_client()
    _CLIENT_RC += 1


async def close_http_client() -> None:
    global _CLIENT, _CLIENT_RC
    _CLIENT_RC = max(0, _CLIENT_RC - 1)
    if _CLIENT_RC == 0 and _CLIENT is not None:
        await _CLIENT.aclose()
        _CLIENT = None


def _host_from_url(url: str) -> str:
    try:
        return url.split("/")[2]
    except Exception:
        return ""


def _breaker_state(host: str) -> dict[str, Any]:
    with _BR_LOCK:
        st = _BREAKER.get(host)
        if st is None:
            st = {"fail": 0, "opened_at": 0.0, "open": False, "half": False}
            _BREAKER[host] = st
        return st


def _should_block(host: str) -> bool:
    st = _breaker_state(host)
    if st["open"]:
        elapsed = time.time() - float(st["opened_at"] or 0.0)
        if elapsed < _RESET_TIMEOUT:
            return True
        with _BR_LOCK:
            st["open"] = False
            st["half"] = True
            _BREAKER[host] = st
    return False


def _record_success(host: str) -> None:
    with _BR_LOCK:
        _BREAKER[host] = {"fail": 0, "opened_at": 0.0, "open": False, "half": False}


def _record_failure(host: str) -> None:
    st = _breaker_state(host)
    with _BR_LOCK:
        st["fail"] = int(st["fail"]) + 1
        if st["fail"] >= _FAIL_THRESHOLD:
            st["open"] = True
            st["opened_at"] = time.time()
            st["half"] = False
        _BREAKER[host] = st


async def _request_with_retry(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    cookies: dict[str, str] | None = None,
    json: dict[str, Any] | None = None,
    max_attempts: int = 3,
    backoff_base: float = 0.2,
) -> httpx.Response:
    host = _host_from_url(url)
    client = _get_client()
    for attempt in range(max_attempts):
        if _should_block(host):
            raise RuntimeError("circuit_open")
        try:
            if method == "GET":
                r = await client.get(url, headers=headers, cookies=cookies)
            else:
                r = await client.post(url, headers=headers, cookies=cookies, json=json)
            if r.status_code >= 500:
                _record_failure(host)
                await asyncio.sleep(backoff_base * (2**attempt))
                continue
            _record_success(host)
            return r
        except Exception:
            _record_failure(host)
            await asyncio.sleep(backoff_base * (2**attempt))
    raise RuntimeError("request_failed")


async def _exchange_token(token: str) -> dict[str, Any]:
    url = f"https://account.seewo.com/seewo-account/api/v1/auth/{token}/exchange"
    headers = {
        "X-APM-TraceId": secrets.token_hex(16),
        "x-auth-app": "EasiNote5",
        "x-auth-brand": "",
        "x-auth-timestamp": str(int(time.time() * 1000)),
    }
    cookies = {
        "x-auth-app": "EasiNote5",
        "x-auth-brand": "",
        "client_version": "5.2.4.8615",
        "client_build_version": "108615",
        "client_flags": "tabs",
        "pt_token": token,
    }
    r = await _request_with_retry("GET", url, headers=headers, cookies=cookies)
    try:
        data = r.json()
        logger.trace("请求的返回信息: {}", str(data))
        return data
    except Exception:
        return {}


async def _is_token_invalid(token: str) -> bool:
    try:
        logger.trace("开始检查token有效性")
        data = await _exchange_token(token)
        code = data.get("statusCode")
        if code == TOKEN_INVALID_CODE:
            try:
                r = get_cache()
                raw = await r.get(f"token_index:{token}")
                uid = None
                if raw:
                    try:
                        idx = json.loads(raw)
                    except Exception:
                        idx = {}
                    uid = idx.get("uid")
                logger.warning("token疑似过期: 账号uid({}): {}", str(uid or "unknown"), str(code))
                logger.trace("请求的返回信息: {}", str(data))
            except Exception:
                pass
            return True
        return False
    except Exception:
        return False


async def is_token_invalid(token: str) -> bool:
    return await _is_token_invalid(token)


async def user_login(userid: str, password_plain: str) -> dict[str, Any]:
    md5_pwd = hashlib.md5(password_plain.encode("utf-8")).hexdigest()
    cache_key = f"{userid}:{md5_pwd}"
    rc = get_cache()
    cached = await rc.get(f"login:{cache_key}")
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass
    url = "https://edu.seewo.com/api/v1/auth/login"
    payload = {
        "username": userid,
        "password": md5_pwd,
        "captcha": None,
        "phoneCountryCode": "",
    }
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "X-APM-TraceId": secrets.token_hex(16),
        "Cookie": "x-auth-app=EasiNote5; x-auth-token=; acw_tc=",
    }
    try:
        resp = await _request_with_retry("POST", url, headers=headers, json=payload)
        data = resp.json()
        token = data.get("data", {}).get("token")
        if not token or token.endswith("-offline") or (await _is_token_invalid(token)):
            raise RuntimeError("invalid_token")
        u = data.get("data", {}).get("user", {})
        result = {
            "token": token,
            "head_img": u.get("photoUrl") or "",
            "phone": u.get("phone") or userid,
            "joinUnitTime": u.get("joinUnitTime"),
            "cityId": u.get("cityId"),
            "accountId": u.get("accountId"),
            "nickName": u.get("nickName"),
            "user_name": u.get("nickName"),
            "realName": u.get("realName"),
            "username": u.get("username") or userid,
            "user_id": u.get("username") or userid,
            "wechatUid": u.get("wechatUid"),
            "uid": u.get("uid"),
            "appCode": u.get("appCode"),
            "raw": data,
        }
        ex = max(30, int(random.uniform(0.8, 1.2) * LOGIN_TTL))
        await rc.set(f"login:{cache_key}", json.dumps(result, ensure_ascii=False), ex=ex)
        logger.info(
            "账户被登录: usrid({}) : 账户信息({}, {}, {})",
            userid,
            str(result.get("nickName") or ""),
            str(result.get("realName") or ""),
            str(result.get("joinUnitTime")),
        )
    except Exception as err:
        raise HTTPException(status_code=401, detail={"message": "token_invalid", "statusCode": "401"}) from err
    else:
        return result
