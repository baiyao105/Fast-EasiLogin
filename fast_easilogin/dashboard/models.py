"""Dashboard 专用请求/响应模型"""

from typing import Any

from pydantic import BaseModel


class ApiResponse(BaseModel):
    """统一 API 响应"""

    message: str = "success"
    statusCode: str = "200"
    data: Any = None


class AddAccountRequest(BaseModel):
    """添加账户请求"""

    userid: str
    password: str
    user_name: str = ""
    head_img: str = ""


class AccountItem(BaseModel):
    """账户列表项"""

    pt_nickname: str
    pt_appid: str
    pt_userid: str
    pt_username: str
    pt_photourl: str | None = None
    status: str = "inactive"
    login_count: int = 0
    last_login: str | None = None
    phone: str = ""
