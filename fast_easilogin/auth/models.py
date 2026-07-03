import hashlib
import random

from pydantic import BaseModel, Field


def _mask_str(s: str | None, min_len: int = 10) -> str:
    if not s:
        return "***"
    if len(s) < min_len:
        return s[0] + "***"
    show = max(3, min_len // 3)
    return s[:show] + "***" + s[-2:]


class LoginResult(BaseModel):
    """登录结果"""

    token: str | None = Field(default=None, description="登录token")
    nickName: str | None = Field(default=None, description="昵称")
    realName: str | None = Field(default=None, description="真实姓名")
    joinUnitTime: str | None = Field(default=None, description="加入单位时间")
    head_img: str | None = Field(default=None, description="头像")
    uid: str | None = Field(default=None, description="用户ID")
    unit_id: str | None = Field(default=None, description="单位ID")


class UserIdentityInfo(BaseModel):
    """用户身份信息"""

    uid: str = Field(..., description="用户ID")
    token: str | None = Field(default=None, description="登录token")
    phone: str | None = Field(default=None, description="手机号")
    nickname: str | None = Field(default=None, description="昵称")
    realname: str | None = Field(default=None, description="真实姓名")
    head_img: str | None = Field(default=None, description="头像")
    unit_id: str | None = Field(default=None, description="单位ID")
    unit_name: str | None = Field(default=None, description="单位名称")
    join_unit_time: str | None = Field(default=None, description="加入单位时间")

    @property
    def uid_hash(self) -> str:
        """uid + unit_id 的 MD5"""
        return hashlib.md5(f"{self.uid}_{self.unit_id or ''}".encode(), usedforsecurity=False).hexdigest()

    def masked_str(self, min_len: int = 10) -> str:
        """脱敏后身份摘要"""
        parts = [
            _mask_str(self.realname, min_len),
            _mask_str(self.nickname, min_len),
            _mask_str(self.phone, min_len),
        ]
        random.shuffle(parts)
        result = " | ".join(p for p in parts if p)
        if not result:
            result = _mask_str(self.uid, min_len)
        return result


class UnitAvatar(BaseModel):
    name: str | None = None
    id: str | None = None


class UnitInfo(BaseModel):
    id: str | None = None
    name: str | None = None
    avatar: UnitAvatar | None = None
    joinUnitTime: str | None = None


class UnitRole(BaseModel):
    id: str | None = None
    name: str | None = None


class UnitUser(BaseModel):
    id: str | None = None
    realName: str | None = None
    nickname: str | None = None
    avatar: str | None = None
    jobNumber: str | None = None
    unitRole: UnitRole | None = None


class AggregatedUserInfo(BaseModel):
    """聚合信息"""

    unitInfo: UnitInfo | None = None
    unitUser: UnitUser | None = None
    token: str | None = None


class UserRecord(BaseModel):
    """用户记录"""

    user_id: str = Field(..., description="用户ID")
    phone: str | None = Field(default=None, description="手机号")
    user_nickname: str | None = Field(default=None, description="用户昵称")
    head_img: str | None = Field(default=None, description="头像")
    real_name: str | None = Field(default=None, description="真实姓名")
    unit_id: str | None = Field(default=None, description="学校ID")
    unit_name: str | None = Field(default=None, description="学校名称")
    token: str | None = Field(default=None, description="登录token")
    refresh_token: str | None = Field(default=None, description="刷新token")
    active: bool = Field(default=True, description="是否激活")


class UserInfoExtendVo(BaseModel):
    """扩展信息"""

    headImage: str | None = Field(default=None, description="头像")
    realName: str | None = Field(default=None, description="真实姓名")
    nickname: str | None = Field(default=None, description="昵称")
    nickName: str | None = Field(default=None, description="昵称")
    uid: str | None = Field(default=None, description="用户ID")
    unitId: str | None = Field(default=None, description="学校ID")
    jobNumber: str | None = Field(default=None, description="工号")
    joinUnitTime: str | None = Field(default=None, description="加入学校时间")
    unitName: str | None = Field(default=None, description="学校名称")
