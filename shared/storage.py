from __future__ import annotations

import asyncio
import json
from pathlib import Path

from diskcache import Cache

from .models import UserRecord

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
USER_FILE = DATA_DIR / "user_data.json"
APPSETTINGS_FILE = DATA_DIR / "appsettings.json"
USERS_CACHE: dict[str, UserRecord] | None = None
USERS_CACHE_MTIME: float | None = None
_CACHE: Cache | None = None
_ACACHE: AsyncCache | None = None


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_users() -> dict[str, UserRecord]:
    ensure_data_dir()
    if not USER_FILE.exists():
        return {}
    mtime = USER_FILE.stat().st_mtime
    global USERS_CACHE, USERS_CACHE_MTIME
    if USERS_CACHE is not None and mtime == USERS_CACHE_MTIME:
        return USERS_CACHE
    with USER_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    raw = data.get("users", {})
    USERS_CACHE = {
        k: UserRecord(
            userid=k,
            password=v.get("password", ""),
            user_nickname=(v.get("user_nickname") or v.get("user_name") or ""),
            user_realname=v.get("user_realname"),
            head_img=v.get("head_img", ""),
            pt_timestamp=v.get("pt_timestamp"),
            user_id=v.get("user_id"),
        )
        for k, v in raw.items()
    }
    USERS_CACHE_MTIME = mtime
    return USERS_CACHE


def save_users(users: dict[str, UserRecord]) -> None:
    ensure_data_dir()
    payload = {
        "users": {
            u.userid: {
                "password": u.password,
                "user_nickname": u.user_nickname,
                "user_realname": u.user_realname,
                "head_img": u.head_img,
                "pt_timestamp": u.pt_timestamp,
                "user_id": u.user_id,
            }
            for u in users.values()
        }
    }
    with USER_FILE.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    global USERS_CACHE, USERS_CACHE_MTIME
    USERS_CACHE = users.copy()
    USERS_CACHE_MTIME = USER_FILE.stat().st_mtime


def load_appsettings() -> dict:
    ensure_data_dir()
    default = {
        "port": 24300,
        "mitmproxy": {
            "enable": True,
            "listen_host": "127.0.0.1",
            "listen_port": 24300,
            "script": "proxy/mitm_local_id.py",
        },
    }
    if APPSETTINGS_FILE.exists():
        with APPSETTINGS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if "port" not in data:
            data["port"] = default["port"]
        if "mitmproxy" not in data:
            data["mitmproxy"] = default["mitmproxy"]
        return data
    with APPSETTINGS_FILE.open("w", encoding="utf-8") as f:
        json.dump(default, f, ensure_ascii=False, indent=2)
    return default


class AsyncCache:
    def __init__(self, cache: Cache):
        self._cache = cache

    async def get(self, key: str) -> bytes | None:
        val = await asyncio.to_thread(self._cache.get, key)
        if val is None:
            return None
        if isinstance(val, bytes):
            return val
        if isinstance(val, str):
            return val.encode("utf-8")
        try:
            return json.dumps(val, ensure_ascii=False).encode("utf-8")
        except Exception:
            return str(val).encode("utf-8")

    async def set(self, key: str, value: str | bytes, ex: int | None = None) -> None:
        data = value.encode("utf-8") if isinstance(value, str) else value
        await asyncio.to_thread(self._cache.set, key, data, expire=ex)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._cache.delete, key)


def get_cache() -> AsyncCache:
    global _CACHE, _ACACHE
    if _ACACHE is not None:
        return _ACACHE
    ensure_data_dir()
    cache_dir = DATA_DIR / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    _CACHE = Cache(str(cache_dir))
    _ACACHE = AsyncCache(_CACHE)
    return _ACACHE


async def cache_json_get(key: str) -> dict:
    r = get_cache()
    raw = await r.get(key)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


async def cache_json_set(key: str, value: dict, ex: int | None = None) -> None:
    r = get_cache()
    data = json.dumps(value, ensure_ascii=False)
    await r.set(key, data, ex=ex)


async def clear_cache() -> None:
    get_cache()
    if _CACHE is not None:
        await asyncio.to_thread(_CACHE.clear)


async def close_cache() -> None:
    global _CACHE, _ACACHE
    if _CACHE is not None:
        await asyncio.to_thread(_CACHE.close)
    _ACACHE = None
    _CACHE = None


async def cache_count(prefix: str) -> int:
    get_cache()
    cache = _CACHE
    if cache is None:
        return 0

    def _count() -> int:
        c = 0
        for k in cache.iterkeys():
            try:
                s = str(k)
            except Exception:
                s = ""
            if s.startswith(prefix):
                c += 1
        return c

    return await asyncio.to_thread(_count)
