import asyncio
import contextlib
import hashlib
import json
import secrets
import time
from typing import Any

import httpx
from fastapi import HTTPException

from shared.models import AggregatedUserInfo, UserIdentityInfo, UserInfoExtendVo
from shared.storage import get_cache, load_users

CLIENT_TIMEOUT = httpx.Timeout(connect=1.0, read=2.0, write=2.0, pool=5.0)
CLIENT_LIMITS = httpx.Limits(max_keepalive_connections=20, max_connections=100)
CLIENT_HTTP2 = True

_CLIENT: httpx.AsyncClient | None = None
LOGIN_TTL = 120.0
USERINFO_TTL = 300.0
_BREAKER: dict[str, dict[str, Any]] = {}
_FAIL_THRESHOLD = 3
_RESET_TIMEOUT = 10.0


def _get_client() -> httpx.AsyncClient:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = httpx.AsyncClient(timeout=CLIENT_TIMEOUT, limits=CLIENT_LIMITS, http2=CLIENT_HTTP2)
    return _CLIENT


async def init_http_client() -> None:
    _get_client()


async def close_http_client() -> None:
    global _CLIENT
    if _CLIENT is not None:
        await _CLIENT.aclose()
        _CLIENT = None


def _host_from_url(url: str) -> str:
    try:
        return url.split("/")[2]
    except Exception:
        return ""


def _breaker_state(host: str) -> dict[str, Any]:
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
        st["open"] = False
        st["half"] = True
        _BREAKER[host] = st
    return False


def _record_success(host: str) -> None:
    _BREAKER[host] = {"fail": 0, "opened_at": 0.0, "open": False, "half": False}


def _record_failure(host: str) -> None:
    st = _breaker_state(host)
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
        return r.json()
    except Exception:
        return {}


async def _is_token_invalid(token: str) -> bool:
    try:
        data = await _exchange_token(token)
        code = data.get("statusCode")
        return code == 40105
    except Exception:
        return False


async def is_token_invalid(token: str) -> bool:
    return await _is_token_invalid(token)


async def fetch_user_info_with_token(token: str) -> dict[str, Any]:
    rc = get_cache()
    cached = await rc.get(f"userinfo:{token}")
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass
    url = "https://edu.seewo.com/api/v2/user/info"
    headers = {"X-APM-TraceId": secrets.token_hex(16)}
    cookies = {"x-auth-app": "EasiNote5", "x-auth-token": token}
    try:
        resp = await _request_with_retry("GET", url, headers=headers, cookies=cookies)
        data = resp.json()
        result = data.get("data", {})
        await rc.set(f"userinfo:{token}", json.dumps(result, ensure_ascii=False), ex=int(USERINFO_TTL))
        return result
    except Exception:
        return {}


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
        await rc.set(f"login:{cache_key}", json.dumps(result, ensure_ascii=False), ex=int(LOGIN_TTL))
        return result
    except Exception:
        raise HTTPException(status_code=401, detail={"message": "token_invalid", "statusCode": "401"})


async def get_user_info(userid: str, password_plain: str) -> dict[str, Any]:
    login = await user_login(userid, password_plain)
    token = login.get("token")
    return await fetch_user_info_with_token(token) if token else {}


async def get_user_info_by_userid(userid: str) -> dict[str, Any]:
    users = load_users()
    record = users.get(userid)
    if not record:
        return {}
    return await get_user_info(userid, record.password)


def select_fields(data: dict[str, Any], fields: list[str] | None) -> dict[str, Any]:
    if not fields:
        return data
    return {k: data.get(k) for k in fields}


async def get_aggregated_user_info(userid: str, password_plain: str, fields: list[str] | None = None) -> dict[str, Any]:
    rc = get_cache()
    md5_pwd = hashlib.md5(password_plain.encode("utf-8")).hexdigest()
    cache_key = f"{userid}:{md5_pwd}"
    cached = await rc.get(f"agg:{cache_key}")
    if cached:
        try:
            full_cached = json.loads(cached)
            return select_fields(full_cached, fields)
        except Exception:
            pass

    login = await user_login(userid, password_plain)
    token = login.get("token")
    info = await fetch_user_info_with_token(token) if token else {}
    ext = info.get("userInfoExtendVo") or {}
    identity = ext.get("userIdentityInfo") or {}
    agg = AggregatedUserInfo(
        token=token,
        head_img=(info.get("photoUrl") or login.get("head_img")),
        photoUrl=info.get("photoUrl"),
        phone=(info.get("phone") or login.get("phone") or userid),
        joinUnitTime=info.get("joinUnitTime") or login.get("joinUnitTime"),
        cityId=info.get("cityId") or login.get("cityId"),
        accountId=info.get("accountId") or login.get("accountId"),
        accountType=info.get("accountType"),
        address=info.get("address"),
        nickName=info.get("nickName") or login.get("nickName"),
        user_name=info.get("nickName") or login.get("user_name"),
        realName=info.get("realName") or login.get("realName"),
        username=info.get("username") or login.get("username") or userid,
        user_id=info.get("username") or login.get("user_id") or userid,
        wechatUid=info.get("wechatUid") or login.get("wechatUid"),
        uid=info.get("uid") or login.get("uid"),
        appCode=info.get("appCode") or login.get("appCode"),
        provinceId=info.get("provinceId"),
        riskLevel=info.get("riskLevel"),
        stageId=info.get("stageId"),
        stageName=info.get("stageName"),
        subjectId=info.get("subjectId"),
        subjectName=info.get("subjectName"),
        unitId=info.get("unitId"),
        unitName=info.get("unitName"),
        version=info.get("version"),
        createTime=info.get("createTime"),
        email=info.get("email"),
        dingdingUid=info.get("dingdingUid"),
        userInfoExtendVo=UserInfoExtendVo(
            picUrl=ext.get("picUrl"),
            unreadMsgCount=ext.get("unreadMsgCount"),
            userIdentityInfo=UserIdentityInfo(otherIdentitys=identity.get("otherIdentitys", [])),
            virtualAvatarPhotoUrl=ext.get("virtualAvatarPhotoUrl"),
        )
        if ext
        else None,
    )
    full = agg.model_dump(exclude_none=True)
    ttl = int(min(LOGIN_TTL, USERINFO_TTL))
    with contextlib.suppress(Exception):
        await rc.set(f"agg:{cache_key}", json.dumps(full, ensure_ascii=False), ex=ttl)
    return select_fields(full, fields)
