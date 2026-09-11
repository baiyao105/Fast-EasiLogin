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
from fast_easilogin.storage.database import get_session_factory
from fast_easilogin.storage.models import (
    AggregatedUserInfo,
    LoginResult,
    UserIdentityInfo,
    UserInfoExtendVo,
)
from fast_easilogin.storage.repositories.accounts import load_credentials
from fast_easilogin.storage.repositories.login_events import record_login_event
from fast_easilogin.storage.store import (
    find_user,
    load_settings,
    set_user_active,
    touch_user_login,
)

_LOGIN_TASKS: dict[tuple[str, str], asyncio.Task[LoginResult]] = {}


async def _record_event(
    services: Services,
    *,
    username: str,
    status: str,
    user_id: str | None = None,
    error_code: str | None = None,
) -> None:
    if services.db_factory is None:
        return
    try:
        async with services.db_factory() as db:
            await record_login_event(
                db,
                username=username,
                status=status,
                user_id=user_id,
                error_code=error_code,
            )
            await db.commit()
        await services.event_bus.publish(
            "login.event",
            {"username": username, "user_id": user_id, "status": status, "error_code": error_code},
        )
    except Exception as err:
        logger.warning("保存登录事件失败: {}", err)


async def authenticate_user(
    services: Services,
    userid: str,
    password_plain: str | None = None,
    userid_for_disable: str | None = None,
    *,
    record_event: bool = True,
) -> LoginResult:
    task_key = (userid, hashlib.sha256((password_plain or "").encode("utf-8")).hexdigest())
    existing = _LOGIN_TASKS.get(task_key)
    if existing is not None and not existing.done():
        return await asyncio.shield(existing)

    task = asyncio.create_task(
        _do_login(services, userid, password_plain, userid_for_disable, record_event=record_event)
    )
    _LOGIN_TASKS[task_key] = task
    try:
        return await asyncio.shield(task)
    finally:
        if _LOGIN_TASKS.get(task_key) is task:
            _LOGIN_TASKS.pop(task_key, None)


async def _do_login(
    services: Services,
    userid: str,
    password_plain: str | None,
    userid_for_disable: str | None = None,
    *,
    record_event: bool = True,
) -> LoginResult:
    if not password_plain:
        factory = get_session_factory()
        async with factory() as db:
            if services.encryptor is None:
                raise NetworkError("凭据加密器未初始化")
            credentials = await load_credentials(db, userid_for_disable or userid, services.encryptor)
            if credentials is None:
                if record_event:
                    await _record_event(
                        services,
                        username=userid,
                        user_id=userid_for_disable,
                        status="invalid_credentials",
                        error_code="credentials_not_found",
                    )
                raise LoginFailedError("未找到用户凭据")
            password_plain = credentials.password
            userid = credentials.account
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
        if record_event:
            await _record_event(services, username=userid, status="upstream", error_code="request_failed")
        raise NetworkError from err
    except (asyncio.CancelledError, KeyboardInterrupt):
        raise
    except Exception as err:
        logger.error("获取token异常: userid={} err={}", userid, err)
        if record_event:
            await _record_event(services, username=userid, status="system", error_code="request_error")
        raise NetworkError from err

    if not token:
        code = data.get("statusCode") if isinstance(data, dict) else None
        msg = data.get("message") if isinstance(data, dict) else None
        logger.warning("登录失败: userid={} code={} message={}", userid, (code or "-"), str(msg or "-"))
        # 控制台验证（record_event=False）不写入活动，也不因失败禁用本地账号
        if record_event:
            factory = get_session_factory()
            async with factory() as db:
                cfg = await load_settings(db)
            should_disable = (userid_for_disable is None) or cfg.global_settings.enable_password_error_disable
            if should_disable:
                target_id = userid_for_disable or userid
                try:
                    async with factory() as db:
                        await set_user_active(db, target_id, False)
                        await db.commit()
                    logger.info("因密码错误自动禁用账户: user_id={}", target_id)
                except Exception as e:
                    logger.error("自动禁用账户失败: {}", str(e))
            else:
                should_disable = False

            await _record_event(
                services,
                username=userid,
                user_id=userid_for_disable,
                status="disabled" if should_disable else "invalid_credentials",
                error_code=str(code or "invalid_credentials"),
            )
        raise LoginFailedError

    u = data.get("data", {}).get("user", {})
    # 希沃返回的业务用户 ID 优先取 uid，其次 username；手机号仅作登录账号，不能当 user_id
    seewo_user_id = u.get("uid") or u.get("userId") or u.get("username")
    result = LoginResult(
        token=token,
        avatar_url=u.get("photoUrl") or "",
        phone=u.get("phone") or userid,
        nick_name=u.get("nickName"),
        user_name=u.get("nickName"),
        real_name=u.get("realName"),
        user_id=seewo_user_id or userid,
        uid=u.get("uid"),
        account_id=u.get("accountId"),
        wechat_uid=u.get("wechatUid"),
        app_code=u.get("appCode"),
        join_unit_time=u.get("joinUnitTime"),
        city_id=u.get("cityId"),
        raw=data,
    )
    if record_event:
        await _record_event(services, username=userid, user_id=result.user_id, status="success")
        if result.user_id:
            factory = get_session_factory()
            async with factory() as db:
                if await touch_user_login(db, result.user_id):
                    await db.commit()
    return result


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
    phone_for_login = (rec.phone or userid) if rec else userid
    login = await authenticate_user(
        services, phone_for_login, password_plain, userid_for_disable=(rec.user_id if rec else None)
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
        user_id=info.get("uid") or info.get("userId") or info.get("username") or login.user_id or userid,
        uid=info.get("uid") or login.uid,
        account_id=info.get("accountId") or login.account_id,
        wechat_uid=info.get("wechatUid") or login.wechat_uid,
        app_code=info.get("appCode") or login.app_code,
        join_unit_time=info.get("joinUnitTime") or login.join_unit_time,
        city_id=info.get("cityId") or login.city_id,
        account_type=info.get("accountType"),
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
