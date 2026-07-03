import asyncio
import contextlib
import hashlib
import json
import random
import secrets
from typing import Any, cast

from loguru import logger

from fast_easilogin.core.constants import (
    AUTH_APP_ANDROID,
    AUTH_REFER_ANDROID,
    CRYPTO_VERSION,
    LOGIN_TTL,
    LOGIN_URL,
    TOKEN_MASK_MIN_LEN,
    USER_AGENT_ANDROID,
    USER_INFO_URL,
    USERINFO_TTL,
)
from fast_easilogin.core.errors import LoginFailedError, NetworkError, RequestFailedError
from fast_easilogin.core.http_client import request_with_retry
from fast_easilogin.storage import (
    find_user,
    get_cache,
    load_appsettings_model,
    load_users,
    load_users_async,
    save_users_async,
)
from fast_easilogin.storage.models import AggregatedUserInfo, LoginResult, UserIdentityInfo, UserInfoExtendVo

_LOGIN_TASKS: dict[str, asyncio.Task[LoginResult]] = {}


async def authenticate_user(userid: str, password_plain: str, userid_for_disable: str | None = None) -> LoginResult:
    """登录认证"""
    existing = _LOGIN_TASKS.get(userid)
    if existing is not None and not existing.done():
        return await existing

    task = asyncio.create_task(_do_login(userid, password_plain, userid_for_disable))
    _LOGIN_TASKS[userid] = task
    try:
        return await task
    finally:
        _LOGIN_TASKS.pop(userid, None)


async def _do_login(userid: str, password_plain: str, userid_for_disable: str | None = None) -> LoginResult:
    """执行登录请求

    先 MD5 再发送
    """
    md5_pwd = hashlib.md5(password_plain.encode("utf-8")).hexdigest()
    payload = {
        "username": userid,
        "password": md5_pwd,
        "captcha": None,
        "phoneCountryCode": "",
    }
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "X-APM-TraceId": secrets.token_hex(16),
        "Cookie": "x-auth-app=EasiNote5; x-auth-token=",
    }
    try:
        resp = await request_with_retry("POST", LOGIN_URL, headers=headers, json=payload)
        data = resp.json()
        token = data.get("data", {}).get("token")
    except RequestFailedError as err:
        logger.error("login请求失败: userid={} err={}", userid, err)
        raise NetworkError from err
    except (asyncio.CancelledError, KeyboardInterrupt):
        raise
    except Exception as err:
        logger.error("获取token异常: userid={} err={}", userid, err)
        raise NetworkError from err

    if not token:
        code = data.get("statusCode") if isinstance(data, dict) else None
        msg = data.get("message") if isinstance(data, dict) else None
        logger.warning("登录失败: userid={} code={} message={}", userid, (code or "-"), str(msg or "-"))
        cfg = load_appsettings_model()
        # 密码错误时自动禁用账户
        should_disable = (userid_for_disable is None) or cfg.Global.enable_password_error_disable
        if should_disable:
            try:
                users = await load_users_async()
                target_user = find_user(userid_for_disable or userid, users)
                if target_user and target_user.active:
                    target_user.active = False
                    users[target_user.user_id] = target_user
                    await save_users_async({target_user.user_id: target_user})
                    logger.info("因密码错误自动禁用账户: user_id={}", target_user.user_id)
            except OSError as e:
                logger.error("自动禁用账户失败: {}", str(e))

        raise LoginFailedError

    u = data.get("data", {}).get("user", {})
    return LoginResult(
        token=token,
        head_img=u.get("photoUrl") or "",
        phone=u.get("phone") or userid,
        joinUnitTime=u.get("joinUnitTime"),
        cityId=u.get("cityId"),
        accountId=u.get("accountId"),
        nickName=u.get("nickName"),
        user_name=u.get("nickName"),
        realName=u.get("realName"),
        username=u.get("username") or userid,
        user_id=u.get("username") or userid,
        wechatUid=u.get("wechatUid"),
        uid=u.get("uid"),
        appCode=u.get("appCode"),
        raw=data,
    )


async def fetch_user_info_with_token(token: str) -> dict[str, Any]:
    """通过 token 获取用户详情

    结果缓存到内存 KV 用于变更检测
    """
    rc = get_cache()
    headers = {"X-auth-refer": AUTH_REFER_ANDROID, "X-Crypto-Version": CRYPTO_VERSION, "User-Agent": USER_AGENT_ANDROID}
    cookies = {"x-auth-app": AUTH_APP_ANDROID, "x-auth-token": token}
    try:
        resp = await request_with_retry("GET", USER_INFO_URL, headers=headers, cookies=cookies)
        data = resp.json()
        result = data.get("data", {})
        uid = str(result.get("uid") or "")
        prev_raw = await rc.get(f"userinfo:last:{uid}") if uid else None
        changed = False
        if prev_raw:
            try:
                prev = json.loads(prev_raw)
            except Exception:
                prev = {}
            changed = prev != result
        if uid:
            await rc.set(
                f"userinfo:last:{uid}",
                json.dumps(result, ensure_ascii=False),
                ex=max(3600, int(USERINFO_TTL)),
            )
        if changed:
            logger.success("账户信息被更新: {}", uid or "-")
            logger.trace("请求的返回信息: {}", str(result))
    except Exception as err:
        masked = f"{token[:6]}...{token[-4:]}" if len(token) > TOKEN_MASK_MIN_LEN else token
        logger.error("账户信息请求失败: token={} err={}", masked or "-", str(err))
        return {}
    else:
        return cast(dict[str, Any], result)


def select_fields(data: dict[str, Any], fields: list[str] | None) -> dict[str, Any]:
    """按字段过滤"""
    if not fields:
        return data
    return {k: data.get(k) for k in fields}


async def get_user_info(userid: str, password_plain: str, fields: list[str] | None = None) -> dict[str, Any]:
    """获取聚合用户信息

    缓存 -> 登录获取 token -> 获取用户详情 -> 合并缓存
    """
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

    users = load_users()
    rec = find_user(userid, users)
    phone_for_login = rec.phone if rec else userid
    login: LoginResult = await authenticate_user(
        phone_for_login, password_plain, userid_for_disable=(rec.user_id if rec else None)
    )
    token = login.token
    info = await fetch_user_info_with_token(token) if token else {}
    ext = info.get("userInfoExtendVo") or {}
    identity = ext.get("userIdentityInfo") or {}
    agg = AggregatedUserInfo(
        token=token,
        head_img=(info.get("photoUrl") or login.head_img),
        photoUrl=info.get("photoUrl"),
        phone=(info.get("phone") or login.phone or userid),
        joinUnitTime=info.get("joinUnitTime") or login.joinUnitTime,
        cityId=info.get("cityId") or login.cityId,
        accountId=info.get("accountId") or login.accountId,
        accountType=info.get("accountType"),
        address=info.get("address"),
        nickName=info.get("nickName") or login.nickName,
        user_name=info.get("nickName") or login.user_name,
        realName=info.get("realName") or login.realName,
        username=info.get("username") or login.username or userid,
        user_id=info.get("username") or login.user_id or userid,
        wechatUid=info.get("wechatUid") or login.wechatUid,
        uid=info.get("uid") or login.uid,
        appCode=info.get("appCode") or login.appCode,
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
    full.pop("token", None)
    ttl = max(30, int(random.uniform(0.8, 1.2) * min(LOGIN_TTL, USERINFO_TTL)))
    with contextlib.suppress(Exception):
        await rc.set(f"agg:{cache_key}", json.dumps(full, ensure_ascii=False), ex=ttl)
    agg_with_token = dict(full)
    agg_with_token["token"] = token
    return select_fields(agg_with_token, fields)
