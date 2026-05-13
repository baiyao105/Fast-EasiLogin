from __future__ import annotations

import asyncio
import contextlib
import json
import threading
import time
import tomllib
from collections import OrderedDict
from pathlib import Path
from typing import cast

import tomlkit
import yaml
from loguru import logger

from fast_easilogin.shared.basic_dir import APPSETTINGS_FILE, APPSETTINGS_TOML, DATA_DIR, USER_DATA_DIR
from fast_easilogin.shared.store.models import CURRENT_SCHEMA_VERSION, AppSettings, UserRecord

toml_dumps = tomlkit.dumps


def _atomic_write(path: Path, data: str, max_retries: int = 3) -> None:
    for attempt in range(max_retries):
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            tmp.write_text(data, encoding="utf-8")
            tmp.replace(path)
        except PermissionError:
            if attempt == max_retries - 1:
                raise
            time.sleep(0.1 * (attempt + 1))
        else:
            return


class AppSettingsManager:
    _instance: AppSettingsManager | None = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, toml_path: Path | None = None, legacy_json_path: Path | None = None):
        if not hasattr(self, "_initialized"):
            self.toml_path = toml_path or APPSETTINGS_TOML
            self.legacy_json_path = legacy_json_path or APPSETTINGS_FILE
            self._cached: AppSettings | None = None
            self._cache_mtime: float = 0.0
            self._initialized = True

    def _load_toml(self) -> dict:
        p = self.toml_path
        if not p.exists():
            return {}
        try:
            raw = p.read_bytes()
            return tomllib.loads(raw.decode("utf-8"))
        except Exception as err:
            logger.error("读取 TOML 失败: path={} err={}", str(p), str(err))
            return {}

    def _merge(self, file_cfg: dict) -> dict:
        defaults = AppSettings().model_dump()
        merged = defaults.copy()
        fc = dict(file_cfg or {})
        if isinstance(fc.get("Global"), dict):
            merged["Global"].update(fc.get("Global") or {})
        for k, v in fc.items():
            if k not in ("Global",):
                merged[k] = v
        merged["schema_version"] = CURRENT_SCHEMA_VERSION
        return merged

    def _validate(self, cfg: dict) -> AppSettings:
        try:
            return AppSettings.model_validate(cfg)
        except Exception as err:
            logger.error("配置校验失败: {}", str(err))
            raise

    def _current_mtime(self) -> float:
        if self.toml_path.exists():
            with contextlib.suppress(OSError):
                return self.toml_path.stat().st_mtime
        return 0.0

    def write(self, cfg: dict) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        text = toml_dumps(cfg)
        _atomic_write(self.toml_path, text)
        self._cached = None

    def load(self) -> AppSettings:
        mtime = self._current_mtime()
        if self._cached is not None and self._cache_mtime == mtime:
            return self._cached
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        file_cfg = self._load_toml()
        if not file_cfg:
            merged = self._merge({})
            try:
                self.write(merged)
            except Exception as err:
                logger.error("写入 TOML 失败: err={}", str(err))
            file_cfg = merged
        cfg = self._merge(file_cfg)
        app_settings = self._validate(cfg)
        self._cached = app_settings
        self._cache_mtime = mtime
        return app_settings


def write_config(cfg: dict) -> None:
    AppSettingsManager().write(cfg)


def load_appsettings_model() -> AppSettings:
    return AppSettingsManager().load()


def load_appsettings() -> dict:
    return load_appsettings_model().model_dump()


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


class InMemoryKVCache:
    def __init__(self, capacity: int):
        self._lock = threading.RLock()
        self._capacity = max(1, int(capacity or 1))
        self._data: OrderedDict[str, tuple[bytes, float | None]] = OrderedDict()

    def _allowed(self, key: str) -> bool:
        return key.startswith(("agg:", "userinfo:last:"))

    async def get(self, key: str) -> bytes | None:
        now = time.time()
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            val, exp = item
            if exp is not None and exp <= now:
                del self._data[key]
                return None
            self._data.move_to_end(key, last=True)
            return val

    async def set(self, key: str, value: str | bytes, ex: int | None = None) -> None:
        if not self._allowed(key):
            return
        data = value.encode("utf-8") if isinstance(value, str) else value
        exp = (time.time() + float(ex)) if ex and ex > 0 else None
        with self._lock:
            if key in self._data:
                del self._data[key]
            self._data[key] = (data, exp)
            while len(self._data) > self._capacity:
                self._data.popitem(last=False)

    async def delete(self, key: str) -> None:
        with self._lock:
            del self._data[key]

    async def clear(self) -> None:
        with self._lock:
            self._data.clear()


class SharedContainer:
    def __init__(self):
        self.users_cache: dict[str, UserRecord] | None = None
        self.users_cache_mtime: float | None = None
        self.mem_cache: InMemoryKVCache | None = None
        self.phone_index: dict[str, str] | None = None

    def get_mem_cache(self) -> InMemoryKVCache:
        if self.mem_cache is not None:
            return self.mem_cache
        capacity = int(load_appsettings_model().Global.cache_max_entries)
        self.mem_cache = InMemoryKVCache(capacity)
        return self.mem_cache


_CONTAINER: SharedContainer | None = None
_CONTAINER_LOCK = threading.Lock()


def _get_container() -> SharedContainer:
    global _CONTAINER  # noqa: PLW0603
    if _CONTAINER is None:
        with _CONTAINER_LOCK:
            if _CONTAINER is None:
                _CONTAINER = SharedContainer()
    return _CONTAINER


def get_cache():
    cont = _get_container()
    return cont.get_mem_cache()


async def cache_json_get(key: str) -> dict:
    r = get_cache()
    raw = await r.get(key)
    if not raw:
        return {}
    try:
        return cast(dict, json.loads(raw))
    except Exception:
        return {}


async def cache_json_set(key: str, value: dict, ex: int | None = None) -> None:
    r = get_cache()
    data = json.dumps(value, ensure_ascii=False)
    await r.set(key, data, ex=ex)


async def clear_cache() -> None:
    cont = _get_container()
    r = cont.get_mem_cache()
    await r.clear()


async def close_cache() -> None:
    cont = _get_container()
    cont.mem_cache = None


_CACHE_LOCK = threading.Lock()


def _latest_profiles_mtime(base_dir: Path) -> float:
    latest = 0.0
    for d in base_dir.glob("*"):
        if not d.is_dir():
            continue
        uid = d.name
        p = base_dir / uid / f"{uid}_profile.yaml"
        if p.exists():
            with contextlib.suppress(OSError):
                latest = max(latest, p.stat().st_mtime)
    return latest


def _read_user_profile(base: Path, uid: str) -> dict:
    p = base / uid / f"{uid}_profile.yaml"
    if not p.exists():
        return {}
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        return data.get("user_info") or data
    except yaml.YAMLError as e:
        logger.error("YAML 解析失败: uid={} err={}", uid, e)
        return {}
    except OSError as e:
        logger.error("读取 profile 失败: uid={} err={}", uid, e)
        return {}


def _user_record_from_info(uid: str, info: dict) -> UserRecord:
    return UserRecord(
        user_id=uid,
        active=bool(info.get("active", True)),
        phone=str(info.get("phone") or ""),
        password=str(info.get("password") or ""),
        user_nickname=str(info.get("user_nickname") or info.get("user_name") or ""),
        user_realname=(info.get("user_realname") or None),
        head_img=str(info.get("head_img") or ""),
        pt_timestamp=(info.get("pt_timestamp") or None),
    )


def load_users() -> dict[str, UserRecord]:
    ensure_data_dir()
    base = USER_DATA_DIR
    base.mkdir(parents=True, exist_ok=True)
    cont = _get_container()
    mtime = _latest_profiles_mtime(base)
    if cont.users_cache is not None and cont.users_cache_mtime == mtime:
        return cont.users_cache

    users: dict[str, UserRecord] = {}
    phone_index: dict[str, str] = {}
    for d in base.glob("*"):
        if not d.is_dir():
            continue
        uid = d.name
        info = _read_user_profile(base, uid)
        if not info:
            continue
        record = _user_record_from_info(uid, info)
        users[uid] = record
        if record.phone:
            phone_index[record.phone] = uid

    cont.users_cache = users
    cont.phone_index = phone_index
    cont.users_cache_mtime = mtime
    return users


def find_user(identifier: str, users: dict[str, UserRecord] | None = None) -> UserRecord | None:
    if users is None:
        users = load_users()
    record = users.get(identifier)
    if record:
        return record
    cont = _get_container()
    uid = cont.phone_index.get(identifier) if cont.phone_index else None
    if uid:
        return users.get(uid)
    return None


def _dump_user_record(base: Path, u: UserRecord) -> None:
    uid = u.user_id
    if not uid:
        return
    d = base / uid
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{uid}_profile.yaml"
    prev_info = _read_user_profile(base, uid)
    created = not p.exists()
    payload = {
        "user_info": {
            "active": u.active,
            "phone": u.phone,
            "password": u.password,
            "user_nickname": u.user_nickname,
            "user_realname": u.user_realname,
            "head_img": u.head_img,
            "pt_timestamp": u.pt_timestamp,
            "user_id": uid,
        }
    }
    text = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
    tmp = p.with_suffix(".yaml.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(p)

    fields = ["active", "phone", "password", "user_nickname", "user_realname", "head_img", "user_id"]
    if created:
        logger.success("创建账户配置: user_id={} nickname={}", uid, u.user_nickname or "-")
    else:
        changed = any((str(prev_info.get(f) or "") != str(payload["user_info"].get(f) or "")) for f in fields)
        if changed:
            changed_fields = [
                f for f in fields if str(prev_info.get(f) or "") != str(payload["user_info"].get(f) or "")
            ]
            logger.success(
                "账户配置更新: user_id={} nickname={} changes={}", uid, u.user_nickname or "-", changed_fields
            )


def save_users(users: dict[str, UserRecord], user_ids: list[str] | None = None) -> None:
    ensure_data_dir()
    base = USER_DATA_DIR
    base.mkdir(parents=True, exist_ok=True)
    ids = set(user_ids) if user_ids is not None else None
    targets = [u for u in users.values() if ids is None or u.user_id in ids]
    for u in targets:
        _dump_user_record(base, u)
    cont = _get_container()
    with _CACHE_LOCK:
        cont.users_cache = users.copy()
        cont.users_cache_mtime = _latest_profiles_mtime(base)
        cont.phone_index = {u.phone: u.user_id for u in users.values() if u.phone}


async def save_users_async(users: dict[str, UserRecord], user_ids: list[str] | None = None) -> bool:
    ensure_data_dir()
    base = USER_DATA_DIR
    base.mkdir(parents=True, exist_ok=True)

    ids = set(user_ids) if user_ids is not None else None

    def _write_many() -> bool:
        try:
            targets = [u for u in users.values() if ids is None or u.user_id in ids]
            for u in targets:
                _dump_user_record(base, u)
        except OSError as e:
            logger.error("保存用户数据失败: {}", e)
            return False
        else:
            return True

    ok = await asyncio.to_thread(_write_many)
    cont = _get_container()
    with _CACHE_LOCK:
        cont.users_cache = users.copy()
        cont.users_cache_mtime = _latest_profiles_mtime(base)
        cont.phone_index = {u.phone: u.user_id for u in users.values() if u.phone}
    return ok


def get_users_mtime() -> float | None:
    ensure_data_dir()
    base = USER_DATA_DIR
    base.mkdir(parents=True, exist_ok=True)
    latest = _latest_profiles_mtime(base)
    return latest if latest > 0 else None
