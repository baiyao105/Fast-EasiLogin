from fastapi import APIRouter, HTTPException

from fast_easilogin.dashboard.models import ApiResponse
from fast_easilogin.storage import load_settings, update_settings
from fast_easilogin.storage.models import SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
async def get_settings():
    settings = await load_settings()
    return ApiResponse(data=settings.model_dump(by_alias=True))


@router.post("")
async def update_settings_api(body: SettingsUpdate):
    update_data = body.model_dump(by_alias=True, exclude_unset=True, exclude_none=True)
    if not update_data:
        return ApiResponse()

    success = await update_settings(update_data)
    if not success:
        raise HTTPException(status_code=500, detail="settings_update_failed")
    return ApiResponse(message="settings_updated")
