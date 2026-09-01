from fastapi import APIRouter, HTTPException
from loguru import logger

from fast_easilogin.dashboard.models import AccountItem, AddAccountRequest, ApiResponse
from fast_easilogin.storage import delete_user, load_users, save_users, user_exists
from fast_easilogin.storage.models import UserRecord

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("")
async def list_accounts():
    users = await load_users()
    data = [
        AccountItem(
            pt_nickname=u.nick_name or "",
            pt_appid=u.user_id,
            pt_userid=u.user_id,
            pt_username=u.real_name or u.user_id,
            pt_photourl=u.avatar_url,
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
    userid = body.userid.strip()
    password = body.password
    if not userid or not password:
        raise HTTPException(status_code=400, detail="userid and password required")

    if await user_exists(userid):
        raise HTTPException(status_code=409, detail="user_already_exists")

    record = UserRecord(
        user_id=userid,
        active=True,
        phone=userid,
        password=password,
        nick_name=body.user_name,
        real_name="",
        avatar_url=body.head_img,
        pt_timestamp=None,
    )
    await save_users({userid: record})
    logger.info("Dashboard 添加账户: user_id={}", userid)
    return ApiResponse(message="account_added")


@router.delete("/{userid}")
async def delete_account(userid: str):
    """删除账户"""
    if not await user_exists(userid):
        raise HTTPException(status_code=404, detail="user_not_found")

    await delete_user(userid)
    logger.info("Dashboard 删除账户: user_id={}", userid)
    return ApiResponse(message="account_deleted")
