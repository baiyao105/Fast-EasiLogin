import asyncio
import random

_INFLIGHT_USERS: set[str] = set()
_INFLIGHT_LOCK = asyncio.Lock()


def ttl_with_jitter(base: float) -> int:
    j = random.uniform(0.8, 1.2)
    return max(5, int(base * j))
