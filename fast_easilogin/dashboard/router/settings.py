from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from fast_easilogin.dashboard.models import ApiResponse
from fast_easilogin.storage import get_db
from fast_easilogin.storage.models import SettingsUpdate
from fast_easilogin.storage.store import load_settings, update_settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
async def get_settings(db: AsyncSession = Depends(get_db)):
    settings = await load_settings(db)
    return ApiResponse(data=settings.model_dump(by_alias=True))


@router.post("")
async def update_settings_api(body: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    update_data = body.model_dump(by_alias=True, exclude_unset=True, exclude_none=True)
    if not update_data:
        return ApiResponse()

    success = await update_settings(db, update_data)
    if not success:
        raise HTTPException(status_code=500, detail="settings_update_failed")
    return ApiResponse(message="settings_updated")
