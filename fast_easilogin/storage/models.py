from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import SQLModel

CURRENT_SCHEMA_VERSION = 1


class UserTable(SQLModel, table=True):
    """用户表"""

    __tablename__ = "users"

    user_id: str = Field(primary_key=True, max_length=128)
    active: bool = Field(default=True, index=True)
    phone: str = Field(default="", max_length=32, index=True)
    password: str = Field(default="")
    nick_name: str = Field(default="", max_length=128)
    real_name: str | None = Field(default=None, max_length=128)
    avatar_url: str = Field(default="")
    pt_timestamp: int | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SettingTable(SQLModel, table=True):
    """配置表 (KV 结构)"""

    __tablename__ = "settings"

    key: str = Field(primary_key=True, max_length=128)
    value: str = Field(default="")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UserRecord(BaseModel):
    """用户记录 (内部)"""

    user_id: str
    active: bool = True
    phone: str = ""
    password: str = Field(exclude=True)
    nick_name: str = ""
    real_name: str | None = None
    avatar_url: str = ""
    pt_timestamp: int | None = None


class UserInfoBase(BaseModel):
    """用户信息基类 (共享字段)"""

    token: str | None = None
    avatar_url: str | None = None
    phone: str | None = None
    nick_name: str | None = None
    user_name: str | None = None
    real_name: str | None = None
    user_id: str | None = None
    uid: str | None = None
    account_id: str | None = None
    wechat_uid: str | None = None
    app_code: str | None = None
    join_unit_time: int | None = None
    city_id: str | None = None


class LoginResult(UserInfoBase):
    """登录结果"""

    raw: dict[str, Any] | None = None


class UserIdentityInfo(BaseModel):
    """用户身份信息"""

    other_identities: list[str] = []


class UserInfoExtendVo(BaseModel):
    """用户扩展信息"""

    pic_url: str | None = None
    unread_msg_count: int | None = None
    user_identity_info: UserIdentityInfo | None = None
    virtual_avatar_url: str | None = None


class AggregatedUserInfo(UserInfoBase):
    """聚合用户信息 (扩展字段)"""

    account_type: int | None = None
    address: str | None = None
    province_id: str | None = None
    risk_level: float | None = None
    stage_id: str | None = None
    stage_name: str | None = None
    subject_id: str | None = None
    subject_name: str | None = None
    unit_id: str | None = None
    unit_name: str | None = None
    version: int | None = None
    create_time: int | None = None
    email: str | None = None
    dingding_uid: str | None = None
    user_info_extend_vo: UserInfoExtendVo | None = None


class SaveUserBody(BaseModel):
    """保存用户请求 (user 类型)"""

    body_type: Literal["user"] = "user"
    userid: str
    password: str
    user_name: str = ""
    head_img: str = ""


class AppSaveDataBody(BaseModel):
    """客户端数据保存body (app 类型)"""

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
    global_settings: GlobalSettings = Field(default_factory=GlobalSettings, alias="Global")
    schema_version: int = CURRENT_SCHEMA_VERSION


class GlobalSettingsUpdate(BaseModel):
    """全局配置更新请求"""

    port: int | None = None
    webui_port: int | None = None
    enable_eventlog: bool | None = None
    enable_password_error_disable: bool | None = None
    auto_restart_on_crash: bool | None = None
    restart_delay_seconds: int | None = None
    cache_max_entries: int | None = None


class SettingsUpdate(BaseModel):
    """设置更新请求"""

    global_settings: GlobalSettingsUpdate | None = Field(default=None, alias="Global")


class DashboardStats(BaseModel):
    """统计数据"""

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


class AccountDeleteRequest(BaseModel):
    """账户删除请求"""

    user_id: str
