from __future__ import annotations

import asyncio
import contextlib
import threading
from pathlib import Path

import yaml
from loguru import logger

from fast_easilogin.shared.basic_dir import USER_DATA_DIR, atomic_write, ensure_data_dir
from fast_easilogin.shared.store.models import UserRecord

_users_cache: dict[str, UserRecord] | None = None
_users_cache_mtime: float | None = None
_phone_index: dict[str, str] | None = None
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
    global _users_cache, _users_cache_mtime, _phone_index  # noqa: PLW0603
    ensure_data_dir()
    base = USER_DATA_DIR
    base.mkdir(parents=True, exist_ok=True)
    mtime = _latest_profiles_mtime(base)
    if _users_cache is not None and _users_cache_mtime == mtime:
        return _users_cache

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

    _users_cache = users
    _phone_index = phone_index
    _users_cache_mtime = mtime
    return users


def find_user(identifier: str, users: dict[str, UserRecord] | None = None) -> UserRecord | None:
    if users is None:
        users = load_users()
    record = users.get(identifier)
    if record:
        return record
    uid = _phone_index.get(identifier) if _phone_index else None
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
    atomic_write(p, text)

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


def _write_users(users: dict[str, UserRecord], user_ids: list[str] | None = None) -> bool:
    global _users_cache, _users_cache_mtime, _phone_index  # noqa: PLW0603
    ensure_data_dir()
    base = USER_DATA_DIR
    base.mkdir(parents=True, exist_ok=True)
    ids = set(user_ids) if user_ids is not None else None
    try:
        targets = [u for u in users.values() if ids is None or u.user_id in ids]
        for u in targets:
            _dump_user_record(base, u)
    except OSError as e:
        logger.error("保存用户数据失败: {}", e)
        return False
    with _CACHE_LOCK:
        _users_cache = users.copy()
        _users_cache_mtime = _latest_profiles_mtime(base)
        _phone_index = {u.phone: u.user_id for u in users.values() if u.phone}
    return True


def save_users(users: dict[str, UserRecord], user_ids: list[str] | None = None) -> None:
    _write_users(users, user_ids)


async def save_users_async(users: dict[str, UserRecord], user_ids: list[str] | None = None) -> bool:
    return await asyncio.to_thread(_write_users, users, user_ids)


def get_users_mtime() -> float | None:
    ensure_data_dir()
    base = USER_DATA_DIR
    base.mkdir(parents=True, exist_ok=True)
    latest = _latest_profiles_mtime(base)
    return latest if latest > 0 else None
