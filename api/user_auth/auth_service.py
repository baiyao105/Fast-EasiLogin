import hashlib
import secrets
import time
from typing import Any

from fastapi import HTTPException
from loguru import logger

from shared.constants import TOKEN_INVALID_CODE
from shared.errors import CircuitOpenError, RequestFailedError
from shared.http_client import request_with_retry


async def _exchange_token(token: str, *, max_attempts: int = 3) -> dict[str, Any]:
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
    r = await request_with_retry("GET", url, headers=headers, cookies=cookies, max_attempts=max_attempts)
    try:
        data = r.json()
    except Exception:
        return {}
    else:
        logger.trace("请求的返回信息: {}", str(data))
        return data


# async def _is_token_invalid(token: str, *, fast: bool = False) -> bool:
#     try:
#         logger.trace("开始检查token有效性")
#         data = await _exchange_token(token, max_attempts=(1 if fast else 3))
#         code = data.get("statusCode")
#         invalid = code == TOKEN_INVALID_CODE
#         if invalid:
#             try:
#                 r = get_cache()
#                 raw = await r.get(f"token_index:{token}")
#                 uid = None
#                 if raw:
#                     try:
#                         idx = json.loads(raw)
#                     except Exception:
#                         idx = {}
#                     uid = idx.get("uid")
#                 if uid:
#                     logger.warning("token疑似过期: 账号uid({}): {}", str(uid or "-"), str(code))
#                 logger.trace("请求的返回信息: {}", str(data))
#             except Exception:
#                 pass
#     except Exception:
#         return False
#     else:
#         return invalid


# async def is_token_invalid(token: str, *, fast: bool = False) -> bool:
#     return await _is_token_invalid(token, fast=fast)


async def check_token_status(token: str, *, max_attempts: int = 3) -> tuple[bool, int | None, dict[str, Any]]:
    data = await _exchange_token(token, max_attempts=max_attempts)
    code = data.get("statusCode") if isinstance(data, dict) else None
    invalid = code == TOKEN_INVALID_CODE
    return invalid, code, data if isinstance(data, dict) else {}


async def user_login(userid: str, password_plain: str) -> dict[str, Any]:
    md5_pwd = hashlib.md5(password_plain.encode("utf-8")).hexdigest()
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
        resp = await request_with_retry("POST", url, headers=headers, json=payload)
        data = resp.json()
        token = data.get("data", {}).get("token")
    except (RequestFailedError, CircuitOpenError) as err:
        logger.error("网络错误: login请求失败: userid={} err={}", userid, str(err))
        raise HTTPException(status_code=504, detail={"message": "network_error", "statusCode": "504"}) from err
    except Exception as err:
        logger.error("获取token异常: userid={} err={}", userid, str(err))
        raise HTTPException(status_code=504, detail={"message": "network_error", "statusCode": "504"}) from err

    if not token:
        code = data.get("statusCode") if isinstance(data, dict) else None
        msg = data.get("message") if isinstance(data, dict) else None
        logger.warning("登录失败: userid={} code={} message={}", userid, (code or "-"), str(msg or "-"))
        raise HTTPException(status_code=401, detail={"message": "token_invalid", "statusCode": "401"})

    u = data.get("data", {}).get("user", {})
    return {
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
