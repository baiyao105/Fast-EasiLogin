import asyncio
import hashlib
import secrets

from loguru import logger

from fast_easilogin.shared.constants import LOGIN_URL
from fast_easilogin.shared.errors import LoginFailedError, NetworkError, RequestFailedError
from fast_easilogin.shared.http_client import request_with_retry
from fast_easilogin.shared.store import find_user, load_appsettings_model, load_users_async, save_users_async
from fast_easilogin.shared.store.models import LoginResult

_LOGIN_TASKS: dict[str, asyncio.Task] = {}


async def user_login(userid: str, password_plain: str, userid_for_disable: str | None = None) -> LoginResult:
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
