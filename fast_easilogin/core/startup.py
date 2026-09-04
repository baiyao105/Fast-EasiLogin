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
    import asyncio  # noqa: PLC0415

    return asyncio.run(load_app_settings())


def check_ports(api_port: int, dashboard_port: int) -> None:
    if not is_port_available("0.0.0.0", api_port):
        raise RuntimeError(f"端口 {api_port} 已被占用")  # noqa: TRY003
    if not is_port_available("127.0.0.1", dashboard_port):
        raise RuntimeError(f"端口 {dashboard_port} 已被占用")  # noqa: TRY003
