from __future__ import annotations

import asyncio
import hashlib
import secrets
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from fast_easilogin.core.constants import (
    AUTH_APP_ANDROID,
    AUTH_REFER_ANDROID,
    CRYPTO_VERSION,
    HTTP_SERVER_ERROR,
    LOGIN_URL,
    TOKEN_MASK_MIN_LEN,
    USER_AGENT_ANDROID,
    USER_INFO_URL,
)
from fast_easilogin.core.errors import LoginFailedError, NetworkError, RequestFailedError
from fast_easilogin.core.services import Services
from fast_easilogin.storage.models import (
    AggregatedUserInfo,
    LoginResult,
    UserIdentityInfo,
    UserInfoExtendVo,
)
from fast_easilogin.storage.store import (
    find_user,
    load_settings,
    set_user_active,
)

_LOGIN_TASKS: dict[str, asyncio.Task[LoginResult]] = {}


async def authenticate_user(
    services: Services,
    db: AsyncSession,
    userid: str,
    password_plain: str,
    userid_for_disable: str | None = None,
) -> LoginResult:
    existing = _LOGIN_TASKS.get(userid)
    if existing is not None and not existing.done():
        return await existing

    task = asyncio.create_task(_do_login(services, db, userid, password_plain, userid_for_disable))
    _LOGIN_TASKS[userid] = task
    try:
        return await task
    finally:
        _LOGIN_TASKS.pop(userid, None)


async def _do_login(
    services: Services,
    db: AsyncSession,
    userid: str,
    password_plain: str,
    userid_for_disable: str | None = None,
) -> LoginResult:
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
        resp = await services.http.post(LOGIN_URL, headers=headers, json=payload)
        if resp.status_code >= HTTP_SERVER_ERROR:
            raise RequestFailedError(message=f"服务端错误: status={resp.status_code}", url=LOGIN_URL)
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
        cfg = await load_settings(db)
        should_disable = (userid_for_disable is None) or cfg.global_settings.enable_password_error_disable
        if should_disable:
            target_id = userid_for_disable or userid
            try:
                await set_user_active(db, target_id, False)
                logger.info("因密码错误自动禁用账户: user_id={}", target_id)
            except Exception as e:
                logger.error("自动禁用账户失败: {}", str(e))

        raise LoginFailedError

    u = data.get("data", {}).get("user", {})
    return LoginResult(
        token=token,
        avatar_url=u.get("photoUrl") or "",
        phone=u.get("phone") or userid,
        nick_name=u.get("nickName"),
        user_name=u.get("nickName"),
        real_name=u.get("realName"),
        user_id=u.get("username") or userid,
        uid=u.get("uid"),
        account_id=u.get("accountId"),
        wechat_uid=u.get("wechatUid"),
        app_code=u.get("appCode"),
        join_unit_time=u.get("joinUnitTime"),
        city_id=u.get("cityId"),
        raw=data,
    )


async def fetch_user_info(services: Services, token: str) -> dict[str, Any]:
    headers = {"X-auth-refer": AUTH_REFER_ANDROID, "X-Crypto-Version": CRYPTO_VERSION, "User-Agent": USER_AGENT_ANDROID}
    cookies = {"x-auth-app": AUTH_APP_ANDROID, "x-auth-token": token}
    try:
        resp = await services.http.get(USER_INFO_URL, headers=headers, cookies=cookies)
        data = resp.json()
        return data.get("data", {})
    except Exception as err:
        masked = f"{token[:6]}...{token[-4:]}" if len(token) > TOKEN_MASK_MIN_LEN else token
        logger.error("账户信息请求失败: token={} err={}", masked or "-", str(err))
        return {}


async def get_user_info(
    services: Services,
    db: AsyncSession,
    userid: str,
    password_plain: str,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    rec = await find_user(db, userid)
    phone_for_login = rec.phone if rec else userid
    login = await authenticate_user(
        services, db, phone_for_login, password_plain, userid_for_disable=(rec.user_id if rec else None)
    )
    token = login.token
    info = await fetch_user_info(services, token) if token else {}
    ext = info.get("userInfoExtendVo") or {}
    identity = ext.get("userIdentityInfo") or {}
    agg = AggregatedUserInfo(
        token=token,
        avatar_url=info.get("photoUrl") or login.avatar_url,
        phone=info.get("phone") or login.phone or userid,
        nick_name=info.get("nickName") or login.nick_name,
        user_name=info.get("nickName") or login.user_name,
        real_name=info.get("realName") or login.real_name,
        user_id=info.get("username") or login.user_id or userid,
        uid=info.get("uid") or login.uid,
        account_id=info.get("accountId") or login.account_id,
        wechat_uid=info.get("wechatUid") or login.wechat_uid,
        app_code=info.get("appCode") or login.app_code,
        join_unit_time=info.get("joinUnitTime") or login.join_unit_time,
        city_id=info.get("cityId") or login.city_id,
        account_type=info.get("accountType"),
        address=info.get("address"),
        province_id=info.get("provinceId"),
        risk_level=info.get("riskLevel"),
        stage_id=info.get("stageId"),
        stage_name=info.get("stageName"),
        subject_id=info.get("subjectId"),
        subject_name=info.get("subjectName"),
        unit_id=info.get("unitId"),
        unit_name=info.get("unitName"),
        version=info.get("version"),
        create_time=info.get("createTime"),
        email=info.get("email"),
        dingding_uid=info.get("dingdingUid"),
        user_info_extend_vo=UserInfoExtendVo(
            pic_url=ext.get("picUrl"),
            unread_msg_count=ext.get("unreadMsgCount"),
            user_identity_info=UserIdentityInfo(other_identities=identity.get("otherIdentitys", [])),
            virtual_avatar_url=ext.get("virtualAvatarPhotoUrl"),
        )
        if ext
        else None,
    )
    result = agg.model_dump(exclude_none=True)
    if fields:
        result = {k: result.get(k) for k in fields}
    return result
