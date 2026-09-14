from __future__ import annotations

import asyncio
import time
from collections import deque
from datetime import UTC, datetime, timedelta
from itertools import islice

_INFLIGHT_TTL = 120.0


class RuntimeState:
    """进程内共享状态"""

    __slots__ = (
        "_inflight_lock",
        "_inflight_users",
        "_recent_logins",
        "_stats",
    )

    def __init__(self) -> None:
        self._inflight_lock: asyncio.Lock = asyncio.Lock()
        self._inflight_users: dict[str, float] = {}
        self._recent_logins: deque[dict] = deque(maxlen=200)
        self._stats: dict[str, int | float] = {
            "start_time": time.time(),
            "total_logins": 0,
            "success_logins": 0,
            "failed_logins": 0,
        }

    def record_login(self, username: str, ip: str, status: str, head_img: str = "") -> None:
        self._recent_logins.appendleft(
            {
                "username": username,
                "login_time": datetime.now(UTC).isoformat(),
                "ip_address": ip,
                "status": status,
                "head_img": head_img,
            }
        )
        self._stats["total_logins"] += 1
        if status == "success":
            self._stats["success_logins"] += 1
        else:
            self._stats["failed_logins"] += 1

    def get_stats(self) -> dict[str, int | float]:
        return dict(self._stats)

    def get_recent_logins(self, limit: int = 20) -> list[dict]:
        return list(islice(self._recent_logins, limit))

    def get_login_trends(self, hours: int = 24) -> list[dict[str, str | int]]:
        now = datetime.now(UTC)
        cutoff = now - timedelta(hours=hours)
        buckets: dict[str, int] = {}
        for entry in self._recent_logins:
            t = datetime.fromisoformat(entry["login_time"])
            if t < cutoff:
                continue
            key = t.strftime("%Y-%m-%d %H:00")
            buckets[key] = buckets.get(key, 0) + 1
        result: list[dict[str, str | int]] = []
        for i in range(hours, 0, -1):
            t = now - timedelta(hours=i)
            key = t.strftime("%Y-%m-%d %H:00")
            result.append({"time": key, "count": buckets.get(key, 0)})
        return result

    async def acquire_inflight(self, uid: str) -> bool:
        """获取 inflight 锁
        Returns:
            True=已获取，False=已有请求在进行。"""
        async with self._inflight_lock:
            if uid in self._inflight_users:
                return False
            self._inflight_users[uid] = time.time()
            self._cleanup_stale()
            return True

    async def release_inflight(self, uid: str) -> None:
        async with self._inflight_lock:
            self._inflight_users.pop(uid, None)

    def _cleanup_stale(self) -> None:
        now = time.time()
        stale = [uid for uid, ts in self._inflight_users.items() if now - ts > _INFLIGHT_TTL]
        for uid in stale:
            self._inflight_users.pop(uid, None)
