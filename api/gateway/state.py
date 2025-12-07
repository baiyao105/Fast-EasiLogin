import asyncio
import json
import random

from loguru import logger

from api.user_auth.auth_service import check_token_status
from shared.constants import TOKEN_MASK_MIN_LEN
from shared.storage import cache_iter_prefix, get_cache, invalidate_token_cache, load_appsettings_model

_INFLIGHT_USERS: set[str] = set()
_INFLIGHT_LOCK = asyncio.Lock()
_INFLIGHT_TOKENS: set[str] = set()

TOKEN_TTL = int(load_appsettings_model().token_ttl)


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
    r = get_cache()
    while True:
        total = 0
        updated = 0
        invalid = 0
        errors = 0
        try:
            tokens = await cache_iter_prefix("token_index:")
            total = len(tokens)
            for k in tokens:
                try:
                    tok = k.split(":", 1)[1]
                except Exception:
                    tok = ""
                if not tok:
                    continue
                if not await try_mark_inflight(tok):
                    continue
                try:
                    invalid_flag, code, data = await check_token_status(tok)
                    if not invalid_flag:
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
                            updated += 1
                            masked = f"{tok[:6]}...{tok[-4:]}" if len(tok) > TOKEN_MASK_MIN_LEN else tok
                            logger.debug("token续期: userid={} uid={} token={}", userid or "-", uid or "-", masked)
                    else:
                        masked = f"{tok[:6]}...{tok[-4:]}" if len(tok) > TOKEN_MASK_MIN_LEN else tok
                        await invalidate_token_cache(tok)
                        invalid += 1
                        logger.warning(
                            "token失效: code={} token={} data_status={}",
                            code if code is not None else "-",
                            masked,
                            (data.get("statusCode") if isinstance(data, dict) else "-"),
                        )
                except Exception as err:
                    errors += 1
                    masked = f"{tok[:6]}...{tok[-4:]}" if len(tok) > TOKEN_MASK_MIN_LEN else tok
                    # logger.error("token巡检异常: token={} err={}", masked, str(err))
                finally:
                    await clear_inflight(tok)
        except Exception:
            pass
        # logger.info("token巡检统计: 总数={} 更新={} 失效={} 错误={}", total, updated, invalid, errors)
        await asyncio.sleep(interval)
