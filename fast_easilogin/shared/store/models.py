from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

CURRENT_SCHEMA_VERSION = 1


class UserRecord(BaseModel):
    user_id: str
    active: bool = True
    phone: str = ""
    password: str
    user_nickname: str
    user_realname: str | None = None
    head_img: str
    pt_timestamp: int | None = None


class SaveUserBody(BaseModel):
    body_type: Literal["user"] = "user"
    userid: str
    password: str
    user_name: str = ""
    head_img: str = ""


class AppSaveDataBody(BaseModel):
    body_type: Literal["app"] = "app"
    pt_appid: str
    pt_type: str
    pt_sysicourl: list[str] = []
    pt_userid: str
    pt_token: str
    pt_nickname: str | None = None
    pt_username: str
    pt_photourl: str | None = None
    pt_timestamp: int
    pt_session: str | None = None


class UserInfoRequest(BaseModel):
    user_id: str
    password: str
    fields: list[str] | None = None


class UserIdentityInfo(BaseModel):
    otherIdentitys: list[str] = []


class UserInfoExtendVo(BaseModel):
    picUrl: str | None = None
    unreadMsgCount: int | None = None
    userIdentityInfo: UserIdentityInfo | None = None
    virtualAvatarPhotoUrl: str | None = None


class AggregatedUserInfo(BaseModel):
    token: str | None = None
    head_img: str | None = None
    photoUrl: str | None = None
    phone: str | None = None
    joinUnitTime: int | None = None
    cityId: str | None = None
    accountId: str | None = None
    accountType: int | None = None
    address: str | None = None
    nickName: str | None = None
    user_name: str | None = None
    realName: str | None = None
    username: str | None = None
    user_id: str | None = None
    wechatUid: str | None = None
    uid: str | None = None
    appCode: str | None = None
    provinceId: str | None = None
    riskLevel: float | None = None
    stageId: str | None = None
    stageName: str | None = None
    subjectId: str | None = None
    subjectName: str | None = None
    unitId: str | None = None
    unitName: str | None = None
    version: int | None = None
    createTime: int | None = None
    email: str | None = None
    dingdingUid: str | None = None
    userInfoExtendVo: UserInfoExtendVo | None = None


class LoginResult(BaseModel):
    token: str
    head_img: str = ""
    phone: str = ""
    joinUnitTime: int | None = None
    cityId: str | None = None
    accountId: str | None = None
    nickName: str | None = None
    user_name: str | None = None
    realName: str | None = None
    username: str | None = None
    user_id: str | None = None
    wechatUid: str | None = None
    uid: str | None = None
    appCode: str | None = None
    raw: dict[str, Any] | None = None


class OkResponse(BaseModel):
    message: str = "success"
    statusCode: str = "200"


class DataResponse(OkResponse):
    data: Any = None


class GlobalSettings(BaseModel):
    port: int = 24300
    enable_eventlog: bool = True
    auto_restart_on_crash: bool = True
    restart_delay_seconds: int = 3
    cache_max_entries: int = 512
    enable_password_error_disable: bool = False


class AppSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    Global: GlobalSettings = GlobalSettings()
    schema_version: int = CURRENT_SCHEMA_VERSION
