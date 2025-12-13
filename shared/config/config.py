from __future__ import annotations

import asyncio
import contextlib
import json
import threading
import time
import tomllib  # py311
from collections import OrderedDict
from pathlib import Path

import tomlkit
import yaml
from loguru import logger

from shared.basic_dir import APPSETTINGS_FILE, APPSETTINGS_TOML, DATA_DIR, USER_DATA_DIR
from shared.config.models import CURRENT_SCHEMA_VERSION, AppSettings, UserRecord

toml_dumps = tomlkit.dumps


def _atomic_write(path: Path, data: str) -> None:
    """原子写入文件"""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(path)


class AppSettingsManager:
    """应用配置管理器"""

    def __init__(self, toml_path: Path | None = None, legacy_json_path: Path | None = None):
        self.toml_path = toml_path or APPSETTINGS_TOML
        self.legacy_json_path = legacy_json_path or APPSETTINGS_FILE

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
        """深合并"""
        defaults = AppSettings().model_dump()
        merged = defaults.copy()
        fc = dict(file_cfg or {})
        if isinstance(fc.get("Global"), dict):
            merged["Global"].update(fc.get("Global") or {})
        if isinstance(fc.get("mitmproxy"), dict):
            merged["mitmproxy"].update(fc.get("mitmproxy") or {})
        for k, v in fc.items():
            if k not in ("Global", "mitmproxy"):
                merged[k] = v
        merged["schema_version"] = CURRENT_SCHEMA_VERSION
        return merged

    def _validate(self, cfg: dict) -> AppSettings:
        try:
            return AppSettings.model_validate(cfg)
        except Exception as err:
            logger.error("配置校验失败: {}", str(err))
            raise

    def write(self, cfg: dict) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        text = toml_dumps(cfg)
        _atomic_write(self.toml_path, text)

    def load(self) -> AppSettings:
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
        return self._validate(cfg)


class UserDataManager:
    """用户数据管理"""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or USER_DATA_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def user_dir(self, uid: str) -> Path:
        d = self.base_dir / uid
        d.mkdir(parents=True, exist_ok=True)
        return d

    def profile_path(self, uid: str) -> Path:
        return self.user_dir(uid) / f"{uid}_profile.yaml"

    def validate_profile(self, data: dict) -> bool:
        return isinstance(data, dict)

    def read_profile(self, uid: str) -> dict:
        p = self.profile_path(uid)
        if not p.exists():
            return {}
        try:
            return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except Exception as err:
            logger.error("读取用户配置失败: uid={} err={}", uid, str(err))
            return {}

    def write_profile(self, uid: str, data: dict) -> None:
        if not self.validate_profile(data):
            raise ValueError()
        text = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
        tmp = self.profile_path(uid).with_suffix(".yaml.tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(self.profile_path(uid))


def write_config(cfg: dict) -> None:
    AppSettingsManager().write(cfg)


def load_appsettings_model() -> AppSettings:
    return AppSettingsManager().load()


def load_appsettings() -> dict:
    """返回配置的 dict 形式"""
    return load_appsettings_model().model_dump()


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


class InMemoryKVCache:
    """仅内存的KV缓存(线程安全), 只允许缓存用户信息内容"""

    def __init__(self, capacity: int):
        self._lock = threading.RLock()
        self._capacity = max(1, int(capacity or 1))
        self._data: OrderedDict[str, tuple[bytes, float | None]] = OrderedDict()

    def _allowed(self, key: str) -> bool:
        # 只允许缓存用户数据内容
        return key.startswith(("agg:", "userinfo:last:"))

    async def get(self, key: str) -> bytes | None:
        now = time.time()
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            val, exp = item
            if exp is not None and exp <= now:
                with contextlib.suppress(Exception):
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
                with contextlib.suppress(Exception):
                    self._data.popitem(last=False)

    async def delete(self, key: str) -> None:
        with self._lock, contextlib.suppress(Exception):
            del self._data[key]

    async def clear(self) -> None:
        with self._lock:
            self._data.clear()


class SharedContainer:
    """共享容器: 用户内存缓存与用户列表缓存"""

    def __init__(self):
        self.users_cache: dict[str, UserRecord] | None = None
        self.users_cache_mtime: float | None = None
        self.mem_cache: InMemoryKVCache | None = None

    def get_mem_cache(self) -> InMemoryKVCache:
        """获取内存缓存实例"""
        if self.mem_cache is not None:
            return self.mem_cache
        capacity = int(load_appsettings_model().Global.cache_max_entries)
        self.mem_cache = InMemoryKVCache(capacity)
        return self.mem_cache


_CONTAINER_REF: list[SharedContainer] = []


def _get_container() -> SharedContainer:
    """获取全局容器单例"""
    if _CONTAINER_REF:
        return _CONTAINER_REF[0]
    _CONTAINER_REF.append(SharedContainer())
    return _CONTAINER_REF[0]


def get_cache():
    """获取全局内存缓存实例"""
    cont = _get_container()
    return cont.get_mem_cache()


async def cache_json_get(key: str) -> dict:
    """读取 JSON 值"""
    r = get_cache()
    raw = await r.get(key)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


async def cache_json_set(key: str, value: dict, ex: int | None = None) -> None:
    """写入 dict 为 JSON 值"""
    r = get_cache()
    data = json.dumps(value, ensure_ascii=False)
    await r.set(key, data, ex=ex)


async def clear_cache() -> None:
    """清空内存缓存内容"""
    cont = _get_container()
    r = cont.get_mem_cache()
    await r.clear()


async def close_cache() -> None:
    """关闭内存缓存"""
    cont = _get_container()
    cont.mem_cache = None


# token缓存相关逻辑已移除


# 统计磁盘缓存键功能已移除


# 收集磁盘缓存键功能已移除


def _latest_profiles_mtime(base_dir: Path) -> float:
    """返回用户 profile.yaml 的最新修改时间, 没有文件时返回 0."""
    latest = 0.0
    for d in base_dir.glob("*"):
        if not d.is_dir():
            continue
        uid = d.name
        p = base_dir / uid / f"{uid}_profile.yaml"
        if p.exists():
            with contextlib.suppress(Exception):
                latest = max(latest, p.stat().st_mtime)
    return latest


def load_users() -> dict[str, UserRecord]:
    """读取所有用户的 profile.yaml 为 UserRecord 字典."""
    ensure_data_dir()
    base = USER_DATA_DIR
    base.mkdir(parents=True, exist_ok=True)
    cont = _get_container()
    mtime = _latest_profiles_mtime(base)
    if cont.users_cache is not None and cont.users_cache_mtime == mtime:
        return cont.users_cache

    users: dict[str, UserRecord] = {}
    for d in base.glob("*"):
        if not d.is_dir():
            continue
        uid = d.name
        p = base / uid / f"{uid}_profile.yaml"
        if not p.exists():
            continue
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except Exception:
            data = {}
        info = data.get("user_info") or {}
        users[uid] = UserRecord(
            userid=uid,
            phone=str(info.get("phone") or ""),
            password=str(info.get("password") or ""),
            user_nickname=str(info.get("user_nickname") or info.get("user_name") or ""),
            user_realname=(info.get("user_realname") or None),
            head_img=str(info.get("head_img") or ""),
            pt_timestamp=(info.get("pt_timestamp") or None),
            user_id=uid,
        )

    cont.users_cache = users
    cont.users_cache_mtime = mtime
    return users


def save_users(users: dict[str, UserRecord]) -> None:
    """保存用户列表到各自的 profile.yaml."""
    ensure_data_dir()
    base = USER_DATA_DIR
    base.mkdir(parents=True, exist_ok=True)

    def _dump(u: UserRecord) -> None:
        uid = u.user_id or u.userid
        if not uid:
            return
        d = base / uid
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{uid}_profile.yaml"
        prev: dict = {}
        created = not p.exists()
        if not created:
            try:
                prev = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            except Exception:
                prev = {}
        prev_info = dict(prev.get("user_info") or prev)
        payload = {
            "user_info": {
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
        fields = ["phone", "password", "user_nickname", "user_realname", "head_img", "user_id"]
        if created:
            logger.success("创建账户配置: user_id={} nickname={}", uid, u.user_nickname or "-")
        else:
            changed = any((str(prev_info.get(f) or "") != str(payload["user_info"].get(f) or "")) for f in fields)
            if changed:
                diff = {
                    f: {
                        "from": str(prev_info.get(f) or ""),
                        "to": str(payload["user_info"].get(f) or ""),
                    }
                    for f in fields
                    if str(prev_info.get(f) or "") != str(payload["user_info"].get(f) or "")
                }
                logger.success("更新账户配置: user_id={} nickname={} changes={}", uid, u.user_nickname or "-", diff)

    for u in users.values():
        _dump(u)

    cont = _get_container()
    cont.users_cache = users.copy()
    cont.users_cache_mtime = _latest_profiles_mtime(base)


async def save_users_async(users: dict[str, UserRecord], expected_mtime: float | None = None) -> bool:
    """异步保存用户列表到各自的 profile.yaml."""
    ensure_data_dir()
    base = USER_DATA_DIR
    base.mkdir(parents=True, exist_ok=True)

    def _write_many() -> None:
        for u in users.values():
            uid = u.user_id or u.userid
            if not uid:
                continue
            d = base / uid
            d.mkdir(parents=True, exist_ok=True)
            p = d / f"{uid}_profile.yaml"
            prev: dict = {}
            created = not p.exists()
            if not created:
                try:
                    prev = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
                except Exception:
                    prev = {}
            prev_info = dict(prev.get("user_info") or prev)
            payload = {
                "user_info": {
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
            fields = ["phone", "password", "user_nickname", "user_realname", "head_img", "user_id"]
            if created:
                logger.success("创建账户配置: user_id={} nickname={}", uid, u.user_nickname or "-")
            else:
                changed = any((str(prev_info.get(f) or "") != str(payload["user_info"].get(f) or "")) for f in fields)
                if changed:
                    diff = {
                        f: {
                            "from": str(prev_info.get(f) or ""),
                            "to": str(payload["user_info"].get(f) or ""),
                        }
                        for f in fields
                        if str(prev_info.get(f) or "") != str(payload["user_info"].get(f) or "")
                    }
                    logger.success("更新账户配置: user_id={} nickname={} changes={}", uid, u.user_nickname or "-", diff)

    await asyncio.to_thread(_write_many)
    cont = _get_container()
    cont.users_cache = users.copy()
    cont.users_cache_mtime = _latest_profiles_mtime(base)
    return True


def get_users_mtime() -> float | None:
    """返回用户 profile.yaml 的最新修改时间, 若无返回 None."""
    ensure_data_dir()
    base = USER_DATA_DIR
    base.mkdir(parents=True, exist_ok=True)
    latest = _latest_profiles_mtime(base)
    return latest if latest > 0 else None
