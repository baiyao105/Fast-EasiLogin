from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from fast_easilogin.dashboard.v1.auth import require_dashboard_auth
from fast_easilogin.dashboard.v1.models import EncryptionRotateRequest, SettingsPatch
from fast_easilogin.storage.encryption.factory import create_encryptor
from fast_easilogin.storage.repositories.accounts import rotate_credentials
from fast_easilogin.storage.store import load_settings, update_settings

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(require_dashboard_auth)])
security_router = APIRouter(tags=["security"], dependencies=[Depends(require_dashboard_auth)])


def _grouped(settings) -> dict:
    g = settings.global_settings
    return {"network": {"api_port": g.port, "dashboard_host": g.dashboard_host, "dashboard_port": g.webui_port}, "runtime": {"enable_eventlog": g.enable_eventlog, "auto_restart_on_crash": g.auto_restart_on_crash, "restart_delay_seconds": g.restart_delay_seconds}, "authentication": {"dashboard_password_required": g.dashboard_password_required, "session_ttl_seconds": g.session_ttl_seconds, "enable_password_error_disable": g.enable_password_error_disable}, "encryption": {"key_source": g.encryption_key_source, "key_version": g.encryption_key_version}}


@router.get("")
async def get_settings(request: Request):
    async with request.app.state.db_factory() as db:
        return _grouped(await load_settings(db))


@router.patch("")
async def patch_settings(body: SettingsPatch, request: Request):
    values = body.model_dump(exclude_none=True)
    if "encryption" in values and "key_source" in values["encryption"]:
        raise HTTPException(status_code=400, detail="use_encryption_rotate_endpoint")
    mapping = {
        "network": {"api_port": "port", "dashboard_port": "webui_port", "dashboard_host": "dashboard_host"},
        "authentication": {},
        "runtime": {},
    }
    update: dict[str, dict] = {"Global": {}}
    for group, entries in values.items():
        for key, value in entries.items():
            update["Global"][mapping.get(group, {}).get(key, key)] = value
    async with request.app.state.db_factory() as db:
        await update_settings(db, update)
        await db.commit()
    return {"settings": await get_settings(request), "restart_required": "network" in values and any(k in values["network"] for k in ("api_port", "dashboard_port", "dashboard_host"))}


@security_router.post("/security/encryption/rotate")
async def rotate_encryption(body: EncryptionRotateRequest, request: Request):
    services = request.app.state.services
    if services.encryptor is None:
        raise HTTPException(status_code=503, detail="credential_encryption_unavailable")
    async with request.app.state.db_factory() as db:
        settings = await load_settings(db)
        new_encryptor = create_encryptor(body.key_source, services.encryptor.key_version + 1)
        try:
            count = await rotate_credentials(db, services.encryptor, new_encryptor)
            await update_settings(db, {"Global": {"encryption_key_source": body.key_source, "encryption_key_version": new_encryptor.key_version}})
            await db.commit()
        except Exception:
            await db.rollback()
            raise
    services.encryptor = new_encryptor
    return {"rotated": count, "key_source": body.key_source, "key_version": new_encryptor.key_version}
