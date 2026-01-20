import asyncio
import random

from shared.store.config import load_appsettings_model

_INFLIGHT_USERS: set[str] = set()
_INFLIGHT_LOCK = asyncio.Lock()
_INFLIGHT_TOKENS: set[str] = set()

TOKEN_TTL = int(load_appsettings_model().Global.token_ttl)


def ttl_with_jitter(base: float) -> int:
    j = random.uniform(0.8, 1.2)
    return max(5, int(base * j))


async def try_mark_inflight(key: str) -> bool:
    async with _INFLIGHT_LOCK:
        if key in _INFLIGHT_TOKENS:
            return False
        _INFLIGHT_TOKENS.add(key)
        return True


async def clear_inflight(key: str) -> None:
    async with _INFLIGHT_LOCK:
        _INFLIGHT_TOKENS.discard(key)


async def token_renew_job(interval: int = 300) -> None:
    await asyncio.Event().wait()
