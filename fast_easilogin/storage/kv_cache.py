from __future__ import annotations

import threading
import time
from collections import OrderedDict

from fast_easilogin.storage.config_manager import load_appsettings_model

_mem_cache: InMemoryKVCache | None = None


class InMemoryKVCache:
    """LRU 内存缓存

    仅允许 agg: / userinfo:last: 前缀的 key
    """

    def __init__(self, capacity: int):
        self._lock = threading.RLock()
        self._capacity = max(1, int(capacity or 1))
        self._data: OrderedDict[str, tuple[bytes, float | None]] = OrderedDict()

    def _allowed(self, key: str) -> bool:
        return key.startswith(("agg:", "userinfo:last:"))

    async def get(self, key: str) -> bytes | None:
        """获取缓存

        过期删除"""
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
        """设置缓存"""
        if not self._allowed(key):
            return
        data = value.encode("utf-8") if isinstance(value, str) else value
        exp = (time.time() + float(ex)) if ex and ex > 0 else None
        with self._lock:
            if key in self._data:
                del self._data[key]
            self._data[key] = (data, exp)
            # 超容量时淘汰最旧条目
            while len(self._data) > self._capacity:
                self._data.popitem(last=False)

    async def delete(self, key: str) -> None:
        """删除缓存"""
        with self._lock:
            del self._data[key]

    async def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._data.clear()


def get_cache() -> InMemoryKVCache:
    """获取全局缓存 (单例)"""
    global _mem_cache  # noqa: PLW0603
    if _mem_cache is not None:
        return _mem_cache
    capacity = int(load_appsettings_model().Global.cache_max_entries)
    _mem_cache = InMemoryKVCache(capacity)
    return _mem_cache


async def clear_cache() -> None:
    """清空全局缓存"""
    r = get_cache()
    await r.clear()


async def close_cache() -> None:
    global _mem_cache  # noqa: PLW0603
    _mem_cache = None
