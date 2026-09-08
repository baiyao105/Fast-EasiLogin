from __future__ import annotations

import asyncio
import time

_INFLIGHT_TTL = 120.0


class RuntimeState:
    """进程内共享状态"""

    __slots__ = (
        "_inflight_lock",
        "_inflight_users",
        "_stats",
    )

    def __init__(self) -> None:
        self._inflight_lock: asyncio.Lock = asyncio.Lock()
        self._inflight_users: dict[str, float] = {}
        self._stats: dict[str, int | float] = {
            "start_time": time.time(),
            "total_logins": 0,
            "success_logins": 0,
            "failed_logins": 0,
        }

    def get_stats(self) -> dict[str, int | float]:
        return dict(self._stats)

    async def acquire_inflight(self, uid: str) -> bool:
        """获取 inflight 锁
        Returns:
            True=已获取, False=已有请求在进行."""
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
