from pydantic import BaseModel, ConfigDict, field_validator

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

    @field_validator("phone", mode="before")
    def _validate_phone(cls, v: str | None) -> str:
        try:
            s = str(v or "").strip()
        except Exception:
            return ""
        if not s:
            return ""
        cn_len = 11
        e164_min = 6
        e164_max = 15
        if s.startswith("+"):
            rest = s[1:]
            return s if rest.isdigit() and e164_min <= len(rest) <= e164_max else ""
        return s if s.isdigit() and len(s) == cn_len and s.startswith("1") else ""


class SaveUserBody(BaseModel):
    userid: str
    password: str
    user_name: str
    head_img: str


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


class UserInfoRequest(BaseModel):
    user_id: str
    password: str
    fields: list[str] | None = None


class AppSaveDataBody(BaseModel):
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


class GlobalSettings(BaseModel):
    port: int = 24301
    token_check_interval: int = 300
    token_ttl: int = 60
    enable_eventlog: bool = True
    auto_restart_on_crash: bool = True
    restart_delay_seconds: int = 3
    cache_max_entries: int = 512
    enable_password_error_disable: bool = False


class AppSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    Global: GlobalSettings = GlobalSettings()
    schema_version: int = CURRENT_SCHEMA_VERSION
