from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from fast_easilogin.dashboard.models import AccountItem, AddAccountRequest, ApiResponse
from fast_easilogin.storage import get_db
from fast_easilogin.storage.models import UserRecord
from fast_easilogin.storage.store import delete_user, get_all_users, save_user, user_exists

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("")
async def list_accounts(db: AsyncSession = Depends(get_db)):
    users = await get_all_users(db)
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
        for u in users
    ]
    return ApiResponse(data=[item.model_dump() for item in data])


@router.post("")
async def add_account(body: AddAccountRequest, db: AsyncSession = Depends(get_db)):
    userid = body.userid.strip()
    password = body.password
    if not userid or not password:
        raise HTTPException(status_code=400, detail="userid and password required")

    if await user_exists(db, userid):
        raise HTTPException(status_code=409, detail="user_already_exists")

    record = UserRecord(
        user_id=userid,
        active=True,
        phone=userid,
        password=password,
        nick_name=body.user_name,
        real_name="",
        avatar_url=body.avatar_url,
        pt_timestamp=None,
    )
    await save_user(db, record)
    await db.commit()
    logger.info("Dashboard 添加账户: user_id={}", userid)
    return ApiResponse(message="account_added")


@router.delete("/{userid}")
async def delete_account(userid: str, db: AsyncSession = Depends(get_db)):
    if not await user_exists(db, userid):
        raise HTTPException(status_code=404, detail="user_not_found")

    await delete_user(db, userid)
    await db.commit()
    logger.info("Dashboard 删除账户: user_id={}", userid)
    return ApiResponse(message="account_deleted")
