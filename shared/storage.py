from __future__ import annotations

import asyncio
import contextlib
import json
import random
import time

from diskcache import Cache

from .basic_dir import APPSETTINGS_FILE, CACHE_DIR, DATA_DIR, USER_FILE
from .models import AppSettings, UserRecord


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


class SharedContainer:
    def __init__(self):
        self.users_cache: dict[str, UserRecord] | None = None
        self.users_cache_mtime: float | None = None
        self.disk_cache: Cache | None = None
        self.async_cache: AsyncCache | None = None

    def get_async_cache(self) -> AsyncCache:
        if self.async_cache is not None:
            return self.async_cache
        ensure_data_dir()
        self.disk_cache = Cache(str(CACHE_DIR))
        self.async_cache = AsyncCache(self.disk_cache)
        return self.async_cache


_CONTAINER_REF: list[SharedContainer] = []


def _get_container() -> SharedContainer:
    if _CONTAINER_REF:
        return _CONTAINER_REF[0]
    _CONTAINER_REF.append(SharedContainer())
    return _CONTAINER_REF[0]


def load_users() -> dict[str, UserRecord]:
    ensure_data_dir()
    if not USER_FILE.exists():
        return {}
    mtime = USER_FILE.stat().st_mtime
    cont = _get_container()
    if cont.users_cache is not None and mtime == cont.users_cache_mtime:
        return cont.users_cache
    with USER_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    raw = data.get("users", {})
    cont.users_cache = {
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
    cont.users_cache_mtime = mtime
    return cont.users_cache


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
    cont = _get_container()
    cont.users_cache = users.copy()
    cont.users_cache_mtime = USER_FILE.stat().st_mtime


def load_appsettings_model() -> AppSettings:
    ensure_data_dir()
    if APPSETTINGS_FILE.exists():
        with APPSETTINGS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        try:
            return AppSettings.model_validate(data)
        except Exception:
            return AppSettings()
    s = AppSettings()
    with APPSETTINGS_FILE.open("w", encoding="utf-8") as f:
        json.dump(s.model_dump(), f, ensure_ascii=False, indent=2)
    return s


def load_appsettings() -> dict:
    return load_appsettings_model().model_dump()


class AsyncCache:
    def __init__(self, cache: Cache):
        self._cache = cache
        self._mem: dict[str, tuple[bytes | None, float]] = {}
        self._miss: dict[str, float] = {}

    def _ttl(self, base: int | float | None) -> float:
        b = float(base or 60.0)
        j = random.uniform(0.8, 1.2)
        return max(5.0, b * j)

    async def get(self, key: str) -> bytes | None:
        now = time.time()
        m = self._miss.get(key)
        if m and m > now:
            return None
        v = self._mem.get(key)
        if v and v[1] > now:
            return v[0]
        val = await asyncio.to_thread(self._cache.get, key)
        if val is None:
            self._miss[key] = now + self._ttl(15)
            return None
        if isinstance(val, bytes):
            data = val
        elif isinstance(val, str):
            data = val.encode("utf-8")
        else:
            try:
                data = json.dumps(val, ensure_ascii=False).encode("utf-8")
            except Exception:
                data = str(val).encode("utf-8")
        self._mem[key] = (data, now + self._ttl(60))
        return data

    async def set(self, key: str, value: str | bytes, ex: int | None = None) -> None:
        now = time.time()
        data = value.encode("utf-8") if isinstance(value, str) else value
        ttl = self._ttl(ex)
        self._mem[key] = (data, now + ttl)
        with contextlib.suppress(Exception):
            del self._miss[key]
        await asyncio.to_thread(self._cache.set, key, data, expire=int(ttl))

    async def delete(self, key: str) -> None:
        with contextlib.suppress(Exception):
            del self._mem[key]
        with contextlib.suppress(Exception):
            del self._miss[key]
        await asyncio.to_thread(self._cache.delete, key)


def get_cache() -> AsyncCache:
    cont = _get_container()
    return cont.get_async_cache()


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
    cont = _get_container()
    r = cont.get_async_cache()
    cache = cont.disk_cache
    if cache is not None:
        await asyncio.to_thread(cache.clear)


async def close_cache() -> None:
    cont = _get_container()
    cache = cont.disk_cache
    if cache is not None:
        await asyncio.to_thread(cache.close)
    cont.async_cache = None
    cont.disk_cache = None


async def invalidate_token_cache(token: str) -> None:
    r = get_cache()
    raw = await r.get(f"token_index:{token}")
    userid: str | None = None
    if raw:
        try:
            idx = json.loads(raw)
        except Exception:
            idx = {}
        await r.delete(f"token_by_user:{idx.get('userid')}")
        uid = idx.get("uid")
        if uid:
            await r.delete(f"token_by_uid:{uid}")
        try:
            userid = idx.get("userid")
        except Exception:
            userid = None
    await r.delete(f"token_index:{token}")
    if userid:
        keys_login = await cache_iter_prefix(f"login:{userid}:")
        for k in keys_login:
            with contextlib.suppress(Exception):
                await r.delete(k)
        keys_agg = await cache_iter_prefix(f"agg:{userid}:")
        for k in keys_agg:
            with contextlib.suppress(Exception):
                await r.delete(k)


async def cache_count(prefix: str) -> int:
    cont = _get_container()
    cache = cont.disk_cache or Cache(str(CACHE_DIR))

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


async def cache_iter_prefix(prefix: str) -> list[str]:
    cont = _get_container()
    cache = cont.disk_cache or Cache(str(CACHE_DIR))

    def _collect() -> list[str]:
        out: list[str] = []
        for k in cache.iterkeys():
            try:
                s = str(k)
            except Exception:
                s = ""
            if s.startswith(prefix):
                out.append(s)
        return out

    return await asyncio.to_thread(_collect)


async def save_users_async(users: dict[str, UserRecord], expected_mtime: float | None = None) -> bool:
    ensure_data_dir()
    if USER_FILE.exists() and expected_mtime is not None:
        cur = USER_FILE.stat().st_mtime
        if cur != expected_mtime:
            return False
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

    def _write() -> None:
        tmp = USER_FILE.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        tmp.replace(USER_FILE)

    await asyncio.to_thread(_write)
    cont = _get_container()
    cont.users_cache = users.copy()
    cont.users_cache_mtime = USER_FILE.stat().st_mtime
    return True


def get_users_mtime() -> float | None:
    ensure_data_dir()
    if USER_FILE.exists():
        return USER_FILE.stat().st_mtime
    return None
