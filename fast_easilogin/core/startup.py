from __future__ import annotations

import socket
import sqlite3

from fast_easilogin.core.basic_dir import DATA_DIR, ensure_data_dir
from fast_easilogin.storage.models import AppSettings


def is_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
        except OSError:
            return False
        else:
            return True


def load_app_settings_sync():
    """同步加载启动配置"""
    db_file = DATA_DIR / "data.db"
    ensure_data_dir()

    if not db_file.exists():
        return AppSettings()
    conn = sqlite3.connect(str(db_file), timeout=30)
    try:
        try:
            row = conn.execute(
                "SELECT port, webui_port, enable_eventlog, auto_restart_on_crash, "
                "restart_delay_seconds, cache_max_entries, enable_password_error_disable "
                "FROM settings WHERE id = 1"
            ).fetchone()
        except sqlite3.OperationalError:
            return AppSettings()
        if row is None:
            return AppSettings()
        return AppSettings.model_validate(
            {
                "Global": {
                    "port": row[0],
                    "webui_port": row[1],
                    "enable_eventlog": bool(row[2]),
                    "auto_restart_on_crash": bool(row[3]),
                    "restart_delay_seconds": row[4],
                    "cache_max_entries": row[5],
                    "enable_password_error_disable": bool(row[6]),
                }
            }
        )
    finally:
        conn.close()


def check_ports(api_port: int, dashboard_port: int | None = None) -> None:
    if not is_port_available("0.0.0.0", api_port):
        raise RuntimeError(f"端口 {api_port} 已被占用")  # noqa: TRY003
    if dashboard_port is not None and not is_port_available("127.0.0.1", dashboard_port):
        raise RuntimeError(f"端口 {dashboard_port} 已被占用")  # noqa: TRY003
