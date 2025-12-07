import contextlib
import hashlib
import json
import random
from typing import Any

from loguru import logger

from shared.constants import LOGIN_TTL, USERINFO_TTL
from shared.http_client import request_with_retry
from shared.models import AggregatedUserInfo, UserIdentityInfo, UserInfoExtendVo
from shared.storage import get_cache, load_users

from .auth_service import user_login


async def fetch_user_info_with_token(token: str) -> dict[str, Any]:
    rc = get_cache()
    cached = await rc.get(f"userinfo:{token}")
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass
    url = "https://edu.seewo.com/api/v2/user/info"
    headers = {"X-APM-TraceId": "trace"}
    cookies = {"x-auth-app": "EasiNote5", "x-auth-token": token}
    try:
        resp = await request_with_retry("GET", url, headers=headers, cookies=cookies)
        data = resp.json()
        result = data.get("data", {})
        ex = max(30, int(random.uniform(0.8, 1.2) * USERINFO_TTL))
        await rc.set(f"userinfo:{token}", json.dumps(result, ensure_ascii=False), ex=ex)
        uid = result.get("uid")
        logger.success("账户信息请求成功: {}", str(uid or "unknown"))
        logger.trace("请求的返回信息: {}", str(result))
    except Exception as err:
        logger.error("账户信息请求失败: {} {}", "unknown", str(err))
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
    ttl = max(30, int(random.uniform(0.8, 1.2) * min(LOGIN_TTL, USERINFO_TTL)))
    with contextlib.suppress(Exception):
        await rc.set(f"agg:{cache_key}", json.dumps(full, ensure_ascii=False), ex=ttl)
    return select_fields(full, fields)
