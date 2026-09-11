from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from fast_easilogin.dashboard.v1.auth import require_dashboard_auth
from fast_easilogin.storage.encryption.env_store import (
    encryption_ready,
    generate_raw_key,
    save_dpapi_key,
    save_environment_key,
    validate_raw_key,
)
from fast_easilogin.storage.store import load_settings, update_settings

router = APIRouter(prefix="/setup", tags=["setup"], dependencies=[Depends(require_dashboard_auth)])


class EncryptionSetupRequest(BaseModel):
    mode: str = Field(default="generate", description="generate | custom")
    key_source: str = Field(default="environment", description="environment | dpapi")
    custom_key: str | None = Field(default=None, description="mode=custom 时的 32 字节 base64 密钥")


@router.get("/status")
async def setup_status(request: Request):
    async with request.app.state.db_factory() as db:
        settings = await load_settings(db)
    g = settings.global_settings
    ready = encryption_ready()
    oobe = bool(getattr(g, "oobe_completed", False)) and ready
    return {
        "oobe_completed": oobe,
        "encryption_ready": ready,
        "key_source": g.encryption_key_source,
        "key_version": g.encryption_key_version,
    }


@router.get("/encryption/key-preview")
async def key_preview():
    """生成一个可预览的新密钥（不落盘），供 OOBE 展示。"""
    return {"key": generate_raw_key()}


@router.post("/encryption")
async def setup_encryption(body: EncryptionSetupRequest, request: Request):
    if body.key_source not in {"environment", "dpapi"}:
        raise HTTPException(status_code=400, detail="invalid_key_source")

    if body.mode == "generate":
        raw_key = generate_raw_key()
    elif body.mode == "custom":
        if not body.custom_key:
            raise HTTPException(status_code=400, detail="custom_key_required")
        try:
            validate_raw_key(body.custom_key)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="invalid_key_format") from exc
        raw_key = body.custom_key
    else:
        raise HTTPException(status_code=400, detail="invalid_mode")

    try:
        if body.key_source == "environment":
            save_environment_key(raw_key)
        else:
            save_dpapi_key(raw_key)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"save_key_failed: {exc}") from exc

    # 写入设置并标记 OOBE 完成
    async with request.app.state.db_factory() as db:
        await update_settings(
            db,
            {
                "Global": {
                    "encryption_key_source": body.key_source,
                    "encryption_key_version": 1,
                    "oobe_completed": True,
                }
            },
        )
        await db.commit()

    services = request.app.state.services
    try:
        from fast_easilogin.storage.encryption.factory import create_encryptor

        services.encryptor = create_encryptor(body.key_source, 1)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"init_encryptor_failed: {exc}") from exc

    return {
        "ok": True,
        "key_source": body.key_source,
        "key_version": 1,
        # 自定义密钥时不回显；生成模式回显一次便于备份
        "key": raw_key if body.mode == "generate" else None,
    }
