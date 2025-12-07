from pydantic import BaseModel


class UserRecord(BaseModel):
    userid: str
    password: str
    user_nickname: str
    user_realname: str | None = None
    head_img: str
    pt_timestamp: int | None = None
    user_id: str | None = None


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


class MitmSettings(BaseModel):
    enable: bool = True
    listen_host: str = "127.0.0.1"
    listen_port: int = 24300
    script: str | None = "proxy/mitm_local_id.py"


class AppSettings(BaseModel):
    port: int = 24300
    mitmproxy: MitmSettings = MitmSettings()
