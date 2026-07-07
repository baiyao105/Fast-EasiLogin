"""账户管理路由"""

from fastapi import APIRouter, HTTPException
from loguru import logger

from fast_easilogin.dashboard.models import AccountItem, AddAccountRequest, ApiResponse
from fast_easilogin.storage import load_users_async, save_users_async
from fast_easilogin.storage.models import UserRecord

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("")
async def list_accounts():
    """获取账户列表"""
    users = await load_users_async()
    data = [
        AccountItem(
            pt_nickname=u.user_nickname or "",
            pt_appid=u.user_id,
            pt_userid=u.user_id,
            pt_username=u.user_realname or u.user_id,
            pt_photourl=u.head_img,
            status="active" if u.active else "inactive",
            login_count=0,
            last_login=None,
            phone=u.phone or "",
        )
        for u in users.values()
    ]
    return ApiResponse(data=[item.model_dump() for item in data])


@router.post("")
async def add_account(body: AddAccountRequest):
    """添加账户"""
    userid = body.userid.strip()
    password = body.password
    if not userid or not password:
        raise HTTPException(status_code=400, detail="userid and password required")

    users = await load_users_async()
    users[userid] = UserRecord(
        user_id=userid,
        active=True,
        phone=userid,
        password=password,
        user_nickname=body.user_name,
        user_realname="",
        head_img=body.head_img,
        pt_timestamp=None,
    )
    await save_users_async(users, user_ids=[userid])
    logger.info("Dashboard 添加账户: user_id={}", userid)
    return ApiResponse(message="account_added")


@router.delete("/{userid}")
async def delete_account(userid: str):
    """删除账户"""
    users = await load_users_async()
    if userid not in users:
        raise HTTPException(status_code=404, detail="user_not_found")
    del users[userid]
    await save_users_async(users)
    logger.info("Dashboard 删除账户: user_id={}", userid)
    return ApiResponse(message="account_deleted")
