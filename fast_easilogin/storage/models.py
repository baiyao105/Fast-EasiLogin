from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlmodel import Field, SQLModel

CURRENT_SCHEMA_VERSION = 1


class UserTable(SQLModel, table=True):
    """用户表"""

    __tablename__ = "users"

    user_id: str = Field(primary_key=True, max_length=128)
    active: bool = Field(default=True, index=True)
    phone: str | None = Field(default=None, max_length=32, index=True, unique=True)
    nick_name: str = Field(default="", max_length=128)
    real_name: str | None = Field(default=None, max_length=128)
    avatar_url: str = Field(default="")
    pt_timestamp: int | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_login_at: datetime | None = None
    # 扩展资料（登录后从希沃用户信息接口刷新）
    school: str | None = Field(default=None, max_length=255)
    stage_name: str | None = Field(default=None, max_length=128)
    subject_name: str | None = Field(default=None, max_length=128)
    join_unit_time: int | None = None
    account_type: int | None = None


class UserCredentialTable(SQLModel, table=True):
    """上游加密凭证"""

    __tablename__ = "user_credentials"

    user_id: str = Field(primary_key=True, foreign_key="users.user_id")
    account_ciphertext: bytes
    account_nonce: bytes
    password_ciphertext: bytes
    password_nonce: bytes
    encryption_algorithm: str
    encryption_key_version: int
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SettingTable(SQLModel, table=True):
    """应用设置表"""

    __tablename__ = "settings"

    id: int = Field(default=1, primary_key=True)
    port: int = Field(default=24300)
    webui_port: int = Field(default=3000)
    dashboard_host: str = Field(default="127.0.0.1", max_length=255)
    enable_eventlog: bool = Field(default=True)
    auto_restart_on_crash: bool = Field(default=True)
    restart_delay_seconds: int = Field(default=3)
    cache_max_entries: int = Field(default=512)
    enable_password_error_disable: bool = Field(default=False)
    dashboard_password_required: bool = Field(default=False)
    session_ttl_seconds: int = Field(default=86400)
    encryption_key_source: str = Field(default="environment", max_length=32)
    encryption_key_version: int = Field(default=1)
    oobe_completed: bool = Field(default=False)
    debug_enabled: bool = Field(default=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DashboardSessionTable(SQLModel, table=True):
    __tablename__ = "dashboard_sessions"

    id: str = Field(primary_key=True, max_length=128)
    created_at: datetime
    expires_at: datetime
    last_seen_at: datetime
    remote_address: str | None = None


class DashboardCredentialTable(SQLModel, table=True):
    __tablename__ = "dashboard_credentials"

    id: int = Field(default=1, primary_key=True)
    password_hash: str
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LoginEventTable(SQLModel, table=True):
    """上游登录记录"""

    __tablename__ = "login_events"

    id: int | None = Field(default=None, primary_key=True)
    user_id: str | None = Field(default=None, index=True, max_length=128)
    username: str = Field(default="", index=True, max_length=128)
    status: str = Field(index=True, max_length=32)
    error_code: str | None = Field(default=None, index=True, max_length=128)
    ip_address: str = Field(default="", max_length=64)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)


class UserRecord(BaseModel):
    """用户记录 (内部)"""

    user_id: str
    active: bool = True
    phone: str | None = None
    password: str = PydanticField(exclude=True)
    nick_name: str = ""
    real_name: str | None = None
    avatar_url: str = ""
    pt_timestamp: int | None = None
    last_login_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    school: str | None = None
    stage_name: str | None = None
    subject_name: str | None = None
    join_unit_time: int | None = None
    account_type: int | None = None


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
    avatar_url: str = ""


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
    dashboard_host: str = "127.0.0.1"
    enable_eventlog: bool = True
    auto_restart_on_crash: bool = True
    restart_delay_seconds: int = 3
    cache_max_entries: int = 512
    enable_password_error_disable: bool = False
    dashboard_password_required: bool = False
    session_ttl_seconds: int = 86400
    encryption_key_source: Literal["environment", "dpapi"] = "environment"
    encryption_key_version: int = 1
    oobe_completed: bool = False
    debug_enabled: bool = False


class AppSettings(BaseModel):
    """应用配置"""

    model_config = ConfigDict(extra="forbid")
    global_settings: GlobalSettings = Field(default_factory=GlobalSettings, alias="Global")
    schema_version: int = CURRENT_SCHEMA_VERSION


class GlobalSettingsUpdate(BaseModel):
    """全局配置更新请求"""

    port: int | None = None
    webui_port: int | None = None
    dashboard_host: str | None = None
    enable_eventlog: bool | None = None
    enable_password_error_disable: bool | None = None
    auto_restart_on_crash: bool | None = None
    restart_delay_seconds: int | None = None
    cache_max_entries: int | None = None
    dashboard_password_required: bool | None = None
    session_ttl_seconds: int | None = None
    encryption_key_source: Literal["environment", "dpapi"] | None = None


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


class AccountDeleteRequest(BaseModel):
    """账户删除请求"""

    user_id: str
