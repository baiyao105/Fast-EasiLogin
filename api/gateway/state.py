import asyncio
import json
import random

from api.user_auth.auth_service import is_token_invalid
from shared.constants import TOKEN_TTL
from shared.storage import cache_iter_prefix, get_cache

_INFLIGHT_USERS: set[str] = set()
_INFLIGHT_LOCK = asyncio.Lock()


def ttl_with_jitter(base: float) -> int:
    j = random.uniform(0.8, 1.2)
    return max(5, int(base * j))


async def token_renew_job() -> None:
    r = get_cache()
    while True:
        try:
            tokens = await cache_iter_prefix("token_index:")
            for k in tokens:
                try:
                    tok = k.split(":", 1)[1]
                except Exception:
                    tok = ""
                if not tok:
                    continue
                try:
                    if not await is_token_invalid(tok):
                        raw = await r.get(f"token_index:{tok}")
                        if raw:
                            try:
                                idx = json.loads(raw)
                            except Exception:
                                idx = {}
                            userid = idx.get("userid")
                            uid = idx.get("uid")
                            if userid:
                                await r.set(f"token_by_user:{userid}", tok, ex=ttl_with_jitter(TOKEN_TTL))
                            if uid:
                                await r.set(f"token_by_uid:{uid}", tok, ex=ttl_with_jitter(TOKEN_TTL))
                            await r.set(
                                f"token_index:{tok}",
                                raw.decode("utf-8") if isinstance(raw, bytes) else raw,
                                ex=ttl_with_jitter(TOKEN_TTL),
                            )
                    else:
                        await r.delete(f"token_index:{tok}")
                except Exception:
                    pass
        except Exception:
            pass
        await asyncio.sleep(30)
