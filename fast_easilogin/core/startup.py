from __future__ import annotations

import socket

from fast_easilogin.storage import load_settings
from fast_easilogin.storage.database import get_db, init_db


def is_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
        except OSError:
            return False
        else:
            return True


async def load_app_settings():
    await init_db()
    async for db in get_db():
        return await load_settings(db)
    return None


def load_app_settings_sync():
    """加载配置(同步)"""
    import asyncio  # noqa: PLC0415
    import contextlib  # noqa: PLC0415
    import json  # noqa: PLC0415
    import sqlite3  # noqa: PLC0415

    from fast_easilogin.core.basic_dir import DATA_DIR, ensure_data_dir  # noqa: PLC0415
    from fast_easilogin.storage.models import AppSettings  # noqa: PLC0415

    db_file = DATA_DIR / "data.db"
    ensure_data_dir()

    async def _init():
        await init_db()

    asyncio.run(_init())
    if not db_file.exists():
        return AppSettings()
    conn = sqlite3.connect(str(db_file))
    try:
        cursor = conn.execute("SELECT key, value FROM settings")
        rows = cursor.fetchall()
        kv = {k: v for k, v in rows}
        if not kv:
            return AppSettings()
        global_data: dict = {}
        for k, v in kv.items():
            if k.startswith("global."):
                field = k.removeprefix("global.")
                with contextlib.suppress(json.JSONDecodeError):
                    global_data[field] = json.loads(v)
        defaults = AppSettings().model_dump(by_alias=True)
        if global_data:
            defaults["Global"].update(global_data)
        return AppSettings.model_validate(defaults)
    finally:
        conn.close()


def check_ports(api_port: int, dashboard_port: int) -> None:
    if not is_port_available("0.0.0.0", api_port):
        raise RuntimeError(f"端口 {api_port} 已被占用")  # noqa: TRY003
    if not is_port_available("127.0.0.1", dashboard_port):
        raise RuntimeError(f"端口 {dashboard_port} 已被占用")  # noqa: TRY003
