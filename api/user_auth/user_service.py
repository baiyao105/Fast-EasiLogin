import contextlib
import hashlib
import json
import random
from typing import Any

from loguru import logger

from shared.constants import LOGIN_TTL, TOKEN_MASK_MIN_LEN, USERINFO_TTL
from shared.http_client import request_with_retry
from shared.store.config import get_cache, load_users
from shared.store.models import AggregatedUserInfo, UserIdentityInfo, UserInfoExtendVo

from .auth_service import user_login


async def fetch_user_info_with_token(token: str) -> dict[str, Any]:
    rc = get_cache()
    url = "https://edu.seewo.com/api/v2/user/info"
    headers = {"X-APM-TraceId": "trace"}
    cookies = {"x-auth-app": "EasiNote5", "x-auth-token": token}
    try:
        resp = await request_with_retry("GET", url, headers=headers, cookies=cookies)
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
        return result


async def get_user_info(userid: str, password_plain: str) -> dict[str, Any]:
    login = await user_login(userid, password_plain)
    token = login.get("token")
    return await fetch_user_info_with_token(token) if token else {}


async def get_user_info_by_userid(userid: str) -> dict[str, Any]:
    users = load_users()
    record = users.get(userid)
    if not record:
        return {}
    # 按照规范: 登录仅使用 phone
    return await get_user_info(record.phone or userid, record.password)


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

    # userid 为 user_id; 登录仅使用 phone, 需要映射
    users = load_users()
    rec = users.get(userid)
    phone_for_login = rec.phone if rec else userid
    login = await user_login(phone_for_login, password_plain)
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
    ttl = max(30, int(random.uniform(0.8, 1.2) * min(LOGIN_TTL, USERINFO_TTL)))
    with contextlib.suppress(Exception):
        await rc.set(f"agg:{cache_key}", json.dumps(full, ensure_ascii=False), ex=ttl)
    return select_fields(full, fields)
