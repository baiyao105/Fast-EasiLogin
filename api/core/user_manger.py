import hashlib
import secrets
from typing import Any

import httpx

from shared.models import AggregatedUserInfo, UserIdentityInfo, UserInfoExtendVo
from shared.storage import load_users


async def fetch_user_info_with_token(token: str) -> dict[str, Any]:
    url = "https://edu.seewo.com/api/v2/user/info"
    headers = {"X-APM-TraceId": secrets.token_hex(16)}
    cookies = {"x-auth-app": "EasiNote5", "x-auth-token": token}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(url, headers=headers, cookies=cookies)
            data = r.json()
            return data.get("data", {})
    except Exception:
        return {}


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
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.post(url, json=payload, headers=headers)
            data = r.json()
            token = data.get("data", {}).get("token")
            u = data.get("data", {}).get("user", {})
            return {
                "token": token or f"{secrets.token_hex(16)}-mock",
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
    except Exception:
        return {
            "token": f"{secrets.token_hex(16)}-offline",
            "head_img": "",
            "phone": userid,
            "joinUnitTime": None,
            "cityId": None,
            "accountId": None,
            "nickName": None,
            "user_name": None,
            "realName": None,
            "username": userid,
            "user_id": userid,
            "wechatUid": None,
            "uid": None,
            "appCode": None,
            "raw": {},
        }


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
    return select_fields(full, fields)
