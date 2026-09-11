from __future__ import annotations

import socket

from fastapi import APIRouter, Depends, HTTPException, Request

from fast_easilogin.dashboard.v1.auth import LOOPBACK_HOSTS, require_dashboard_auth
from fast_easilogin.dashboard.v1.models import EncryptionRotateRequest, SettingsPatch
from fast_easilogin.storage.encryption.factory import create_encryptor
from fast_easilogin.storage.repositories.accounts import rotate_credentials
from fast_easilogin.storage.repositories.dashboard import get_credential
from fast_easilogin.storage.store import load_settings, update_settings

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(require_dashboard_auth)])
security_router = APIRouter(tags=["security"], dependencies=[Depends(require_dashboard_auth)])


def _grouped(settings) -> dict:
    g = settings.global_settings
    return {
        "network": {
            "api_port": g.port,
            "dashboard_host": g.dashboard_host,
            "dashboard_port": g.webui_port,
        },
        "runtime": {
            "enable_eventlog": g.enable_eventlog,
            "auto_restart_on_crash": g.auto_restart_on_crash,
            "restart_delay_seconds": g.restart_delay_seconds,
        },
        "authentication": {
            "dashboard_password_required": g.dashboard_password_required,
            "session_ttl_seconds": g.session_ttl_seconds,
            "enable_password_error_disable": g.enable_password_error_disable,
            "password_set": None,  # filled below
            "force_password_for_host": False,
            "is_loopback": (g.dashboard_host or "").strip().lower() in LOOPBACK_HOSTS
            or not (g.dashboard_host or "").strip(),
        },
        "encryption": {
            "key_source": g.encryption_key_source,
            "key_version": g.encryption_key_version,
        },
        "debug": {
            "enabled": bool(getattr(g, "debug_enabled", False)),
        },
    }


async def _enrich_auth(request: Request, payload: dict) -> dict:
    async with request.app.state.db_factory() as db:
        credential = await get_credential(db)
    host = (payload["network"]["dashboard_host"] or "").strip().lower()
    payload["authentication"]["password_set"] = credential is not None
    payload["authentication"]["force_password_for_host"] = bool(host) and host not in LOOPBACK_HOSTS
    return payload


@router.get("")
async def get_settings(request: Request):
    async with request.app.state.db_factory() as db:
        settings = await load_settings(db)
    return await _enrich_auth(request, _grouped(settings))


def _validate_port(value: int, name: str) -> None:
    if value < 1 or value > 65535:
        raise HTTPException(status_code=400, detail=f"invalid_{name}")
    if value < 1024:
        raise HTTPException(status_code=400, detail=f"{name}_privileged")


def _port_in_use(host: str, port: int) -> bool:
    probe_host = "0.0.0.0" if host in {"", "0.0.0.0"} else host
    if probe_host in {"127.0.0.1", "localhost"}:
        probe_host = "127.0.0.1"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((probe_host, port))
        except OSError:
            return True
        else:
            return False


@router.patch("")
async def patch_settings(body: SettingsPatch, request: Request):
    values = body.model_dump(exclude_none=True)
    if "encryption" in values and "key_source" in values.get("encryption", {}):
        raise HTTPException(status_code=400, detail="use_encryption_rotate_endpoint")

    network = values.get("network") or {}
    if "api_port" in network:
        _validate_port(int(network["api_port"]), "api_port")
    if "dashboard_port" in network:
        _validate_port(int(network["dashboard_port"]), "dashboard_port")

    auth_values = values.get("authentication") or {}
    debug_values = values.get("debug") or {}
    if "session_ttl_seconds" in auth_values:
        ttl = int(auth_values["session_ttl_seconds"])
        if ttl < 60:
            raise HTTPException(status_code=400, detail="session_ttl_too_short")
        if ttl > 30 * 86400:
            raise HTTPException(status_code=400, detail="session_ttl_too_long")

    # 非回环必须已有控制台密码，且不允许关闭密码
    async with request.app.state.db_factory() as db:
        settings = await load_settings(db)
        credential = await get_credential(db)
    target_host = (
        network.get("dashboard_host") if "dashboard_host" in network else settings.global_settings.dashboard_host
    )
    target_host = (target_host or "").strip().lower()
    is_loopback = target_host in LOOPBACK_HOSTS or target_host == ""

    if not is_loopback:
        if credential is None:
            raise HTTPException(status_code=400, detail="password_required_for_remote_host")
        if auth_values.get("dashboard_password_required") is False:
            raise HTTPException(status_code=400, detail="password_required_for_remote_host")

    # 端口占用检测（排除当前自身端口）
    current = settings.global_settings
    if "api_port" in network and int(network["api_port"]) != current.port:
        if _port_in_use("0.0.0.0", int(network["api_port"])):
            raise HTTPException(status_code=400, detail="api_port_in_use")
    if "dashboard_port" in network and int(network["dashboard_port"]) != current.webui_port:
        if _port_in_use(target_host or "127.0.0.1", int(network["dashboard_port"])):
            raise HTTPException(status_code=400, detail="dashboard_port_in_use")

    mapping = {
        "network": {
            "api_port": "port",
            "dashboard_port": "webui_port",
            "dashboard_host": "dashboard_host",
        },
        "authentication": {},
        "runtime": {},
        "debug": {"enabled": "debug_enabled"},
    }
    update: dict[str, dict] = {"Global": {}}
    for group, entries in values.items():
        for key, value in entries.items():
            update["Global"][mapping.get(group, {}).get(key, key)] = value

    async with request.app.state.db_factory() as db:
        await update_settings(db, update)
        await db.commit()
        settings = await load_settings(db)

    # 同步 debug 捕获开关
    if "debug" in values:
        store = getattr(request.app.state.services, "api_capture", None)
        if store is not None:
            store.set_enabled(bool(values["debug"].get("enabled", False)))

    restart_required = "network" in values and any(
        k in values["network"] for k in ("api_port", "dashboard_port", "dashboard_host")
    )
    return {
        "settings": await _enrich_auth(request, _grouped(settings)),
        "restart_required": restart_required,
    }


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
            await update_settings(
                db,
                {
                    "Global": {
                        "encryption_key_source": body.key_source,
                        "encryption_key_version": new_encryptor.key_version,
                    }
                },
            )
            await db.commit()
        except Exception:
            await db.rollback()
            raise
    services.encryptor = new_encryptor
    return {
        "rotated": count,
        "key_source": body.key_source,
        "key_version": new_encryptor.key_version,
    }
