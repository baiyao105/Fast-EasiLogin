import asyncio
import time
from collections import deque
from datetime import UTC, datetime, timedelta
from itertools import islice

# 防并发锁
_INFLIGHT_LOCK = asyncio.Lock()
_INFLIGHT_USERS: dict[str, float] = {}
_INFLIGHT_TTL = 120.0


def _stale_inflight() -> list[str]:
    now = time.time()
    return [uid for uid, ts in _INFLIGHT_USERS.items() if now - ts > _INFLIGHT_TTL]


_stats = {
    "start_time": time.time(),
    "total_logins": 0,
    "success_logins": 0,
    "failed_logins": 0,
}

_recent_logins: deque[dict] = deque(maxlen=200)


def record_login(username: str, ip: str, status: str, head_img: str = "") -> None:
    """记录登录事件"""
    _recent_logins.appendleft(
        {
            "username": username,
            "login_time": datetime.now(UTC).isoformat(),
            "ip_address": ip,
            "status": status,
            "head_img": head_img,
        }
    )
    _stats["total_logins"] += 1
    if status == "success":
        _stats["success_logins"] += 1
    else:
        _stats["failed_logins"] += 1


def get_stats() -> dict:
    """获取登录统计"""
    return {
        "start_time": _stats["start_time"],
        "total_logins": _stats["total_logins"],
        "success_logins": _stats["success_logins"],
        "failed_logins": _stats["failed_logins"],
    }


def get_recent_logins(limit: int = 20) -> list[dict]:
    """最近 N 条登录记录"""
    return list(islice(_recent_logins, limit))


def get_login_trends(hours: int = 24) -> list[dict]:
    """按小时聚合登录趋势"""
    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=hours)
    buckets: dict[str, int] = {}
    for entry in _recent_logins:
        t = datetime.fromisoformat(entry["login_time"])
        if t < cutoff:
            continue
        key = t.strftime("%Y-%m-%d %H:00")
        buckets[key] = buckets.get(key, 0) + 1
    result = []
    for i in range(hours, 0, -1):
        t = now - timedelta(hours=i)
        key = t.strftime("%Y-%m-%d %H:00")
        result.append({"time": key, "count": buckets.get(key, 0)})
    return result
