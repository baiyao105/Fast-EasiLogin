"""设置路由"""

from fastapi import APIRouter, HTTPException, Request

from fast_easilogin.dashboard.models import ApiResponse
from fast_easilogin.storage import load_settings, update_settings
from fast_easilogin.storage.models import SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
async def get_settings():
    """获取应用配置"""
    settings = await load_settings()
    return ApiResponse(data=settings.model_dump())


@router.post("")
async def update_settings_api(body: SettingsUpdate):
    """更新应用配置"""
    update_data = body.model_dump(exclude_unset=True, exclude_none=True)
    if not update_data:
        return ApiResponse()

    success = await update_settings(update_data)
    if not success:
        raise HTTPException(status_code=500, detail="settings_update_failed")
    return ApiResponse(message="settings_updated")


@router.post("/clear-cache")
async def clear_cache_api(request: Request):
    """清空缓存"""
    await request.app.state.services.cache.clear()
    return ApiResponse(message="cache_cleared")
