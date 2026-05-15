import asyncio
import time

_INFLIGHT_LOCK = asyncio.Lock()
_INFLIGHT_USERS: dict[str, float] = {}
_INFLIGHT_TTL = 120.0


def _stale_inflight() -> list[str]:
    now = time.time()
    return [uid for uid, ts in _INFLIGHT_USERS.items() if now - ts > _INFLIGHT_TTL]
