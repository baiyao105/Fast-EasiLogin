from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

CURRENT_SCHEMA_VERSION = 1


class UserRecord(BaseModel):
    """用户记录"""

    user_id: str
    active: bool = True
    phone: str = ""
    password: str
    user_nickname: str
    user_realname: str | None = None
    head_img: str
    pt_timestamp: int | None = None


class SaveUserBody(BaseModel):
    """保存用户请求"""

    body_type: Literal["user"] = "user"
    userid: str
    password: str
    user_name: str = ""
    head_img: str = ""


class AppSaveDataBody(BaseModel):
    """客户端数据保存返回"""

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
    """用户信息查询"""

    user_id: str
    password: str
    fields: list[str] | None = None


class UserIdentityInfo(BaseModel):
    """用户身份信息"""

    otherIdentitys: list[str] = []


class UserInfoExtendVo(BaseModel):
    """用户扩展信息"""

    picUrl: str | None = None
    unreadMsgCount: int | None = None
    userIdentityInfo: UserIdentityInfo | None = None
    virtualAvatarPhotoUrl: str | None = None


class AggregatedUserInfo(BaseModel):
    """聚合用户信息"""

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
    """登录结果"""

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
    """成功响应"""

    message: str = "success"
    statusCode: str = "200"


class DataResponse(OkResponse):
    """带数据的成功响应"""

    data: Any = None


class GlobalSettings(BaseModel):
    """全局配置"""

    port: int = 24300
    webui_port: int = 3000
    enable_eventlog: bool = True
    auto_restart_on_crash: bool = True
    restart_delay_seconds: int = 3
    cache_max_entries: int = 512
    enable_password_error_disable: bool = False


class AppSettings(BaseModel):
    """应用配置"""

    model_config = ConfigDict(extra="forbid")
    Global: GlobalSettings = GlobalSettings()
    schema_version: int = CURRENT_SCHEMA_VERSION


class DashboardStats(BaseModel):
    """webui"""

    service_status: str = "running"
    uptime_seconds: int = 0
    listen_port: int = 24300
    total_logins: int = 0
    success_logins: int = 0
    failed_logins: int = 0


class LoginRecord(BaseModel):
    """登录记录"""

    username: str
    login_time: str
    ip_address: str
    status: str


class LoginTrend(BaseModel):
    """登录趋势数据"""

    time: str
    count: int


class GlobalSettingsUpdate(BaseModel):
    """全局配置更新"""

    port: int | None = None
    webui_port: int | None = None
    enable_eventlog: bool | None = None
    enable_password_error_disable: bool | None = None
    auto_restart_on_crash: bool | None = None
    restart_delay_seconds: int | None = None
    cache_max_entries: int | None = None


class SettingsUpdate(BaseModel):
    """设置更新请求"""

    Global: GlobalSettingsUpdate | None = None
    cache_ttl: int | None = None
    enable_autostart: bool | None = None
    log_level: str | None = None
    enable_logging: bool | None = None


class AccountDeleteRequest(BaseModel):
    """账户删除请求"""

    user_id: str
