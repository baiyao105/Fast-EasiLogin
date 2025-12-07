import hashlib
import json
import random
import secrets
import time
from typing import Any

from fastapi import HTTPException
from loguru import logger

from shared.constants import LOGIN_TTL, TOKEN_INVALID_CODE
from shared.http_client import request_with_retry
from shared.storage import get_cache


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
    r = await request_with_retry("GET", url, headers=headers, cookies=cookies)
    try:
        data = r.json()
    except Exception:
        return {}
    else:
        logger.trace("请求的返回信息: {}", str(data))
        return data


async def _is_token_invalid(token: str) -> bool:
    try:
        logger.trace("开始检查token有效性")
        data = await _exchange_token(token)
        code = data.get("statusCode")
        invalid = code == TOKEN_INVALID_CODE
        if invalid:
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
    except Exception:
        return False
    else:
        return invalid


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
        resp = await request_with_retry("POST", url, headers=headers, json=payload)
        data = resp.json()

        token = data.get("data", {}).get("token")
    except Exception as err:
        raise HTTPException(status_code=401, detail={"message": "token_invalid", "statusCode": "401"}) from err

    if not token or token.endswith("-offline") or (await _is_token_invalid(token)):
        raise HTTPException(status_code=401, detail={"message": "token_invalid", "statusCode": "401"})

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
    return result
