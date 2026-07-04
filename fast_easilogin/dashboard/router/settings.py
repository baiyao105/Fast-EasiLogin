"""设置路由"""

from fastapi import APIRouter

from fast_easilogin.dashboard.models import ApiResponse
from fast_easilogin.storage import clear_cache, load_appsettings_model
from fast_easilogin.storage.config_manager import AppSettingsManager
from fast_easilogin.storage.models import SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
async def get_settings():
    """获取应用配置"""
    settings = load_appsettings_model()
    return ApiResponse(data=settings.model_dump())


@router.post("")
async def update_settings(body: SettingsUpdate):
    """更新应用配置"""
    manager = AppSettingsManager()
    current = manager.load()
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        return ApiResponse()

    current_dict = current.model_dump()

    # 处理 Global 字段更新
    global_update = update_data.get("Global")
    if global_update and "Global" in current_dict:
        for k, v in global_update.items():
            if v is not None:
                current_dict["Global"][k] = v

    # 处理其他顶层字段
    for k, v in update_data.items():
        if k != "Global" and v is not None:
            current_dict[k] = v

    manager.write(current_dict)
    return ApiResponse(message="settings_updated")


@router.post("/clear-cache")
async def clear_cache_api():
    """清空缓存"""
    await clear_cache()
    return ApiResponse(message="cache_cleared")
