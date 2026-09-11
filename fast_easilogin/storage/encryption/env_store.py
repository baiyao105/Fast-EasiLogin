from __future__ import annotations

import base64
import os
import re
import secrets

from fast_easilogin.core.basic_dir import DATA_DIR, atomic_write, ensure_data_dir
from fast_easilogin.storage.encryption.aes_gcm import decode_environment_key
from fast_easilogin.storage.encryption.dpapi import DpapiKeyProvider

ENV_FILE = DATA_DIR / ".env"

_ENV_LINE = re.compile(r"^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$")


def _read_env_file() -> dict[str, str]:
    if not ENV_FILE.exists():
        return {}
    values: dict[str, str] = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        match = _ENV_LINE.match(line)
        if match:
            values[match.group(1)] = match.group(2).strip().strip('"').strip("'")
    return values


def _write_env_file(values: dict[str, str]) -> None:
    ensure_data_dir()
    lines = [f"{key}={value}" for key, value in values.items()]
    atomic_write(ENV_FILE, "\n".join(lines) + "\n")


def load_encryption_env() -> dict[str, str]:
    """合并进程环境变量与 data/.env（进程变量优先）。"""
    file_values = _read_env_file()
    merged = dict(file_values)
    for key in ("FAST_EASILOGIN_ENCRYPTION_KEY", "FAST_EASILOGIN_DPAPI_KEY"):
        env = os.environ.get(key)
        if env:
            merged[key] = env
    return merged


def encryption_ready() -> bool:
    values = load_encryption_env()
    return bool(values.get("FAST_EASILOGIN_ENCRYPTION_KEY") or values.get("FAST_EASILOGIN_DPAPI_KEY"))


def generate_raw_key() -> str:
    """生成 32 字节 AES 密钥的 URL-safe base64。"""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")


def validate_raw_key(key: str) -> None:
    decode_environment_key(key)  # raises if invalid


def save_environment_key(raw_key: str) -> None:
    validate_raw_key(raw_key)
    values = _read_env_file()
    values.pop("FAST_EASILOGIN_DPAPI_KEY", None)
    values["FAST_EASILOGIN_ENCRYPTION_KEY"] = raw_key
    _write_env_file(values)
    os.environ["FAST_EASILOGIN_ENCRYPTION_KEY"] = raw_key
    os.environ.pop("FAST_EASILOGIN_DPAPI_KEY", None)


def save_dpapi_key(raw_key: str) -> str:
    """用 DPAPI 保护密钥并写入 .env，返回保护后的 base64。"""
    validate_raw_key(raw_key)
    key_bytes = decode_environment_key(raw_key)
    protected = DpapiKeyProvider().protect(key_bytes)
    encoded = base64.urlsafe_b64encode(protected).decode("ascii")
    values = _read_env_file()
    values.pop("FAST_EASILOGIN_ENCRYPTION_KEY", None)
    values["FAST_EASILOGIN_DPAPI_KEY"] = encoded
    _write_env_file(values)
    os.environ["FAST_EASILOGIN_DPAPI_KEY"] = encoded
    os.environ.pop("FAST_EASILOGIN_ENCRYPTION_KEY", None)
    return encoded
