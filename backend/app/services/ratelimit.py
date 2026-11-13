from __future__ import annotations

import time

from app.core.config import settings

# ponytail: Redis is optional; first connection failure disables it for the
# process lifetime and we fall back to a process-local sliding window.
# For multi-worker production, Redis must be reachable (it is in docker-compose).
_redis_client = None
_redis_disabled = False

_local: dict[str, list[float]] = {}


def _get_redis():
    global _redis_client, _redis_disabled
    if _redis_disabled:
        return None
    if _redis_client is None:
        try:
            import redis

            _redis_client = redis.Redis.from_url(
                settings.redis_url,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
                decode_responses=True,
            )
            _redis_client.ping()
        except Exception:
            _redis_disabled = True
            _redis_client = None
    return _redis_client


def allow(key: str, *, limit: int = 10, window_seconds: int = 60) -> tuple[bool, int]:
    """Sliding-window rate limit. Returns (allowed, remaining)."""
    now = time.time()
    client = _get_redis()

    if client is not None:
        try:
            rk = f"rl:{key}"
            window_start = now - window_seconds
            client.zremrangebyscore(rk, 0, window_start)
            count = client.zcard(rk)
            if count >= limit:
                return False, 0
            client.zadd(rk, {str(now): now})
            client.expire(rk, window_seconds + 1)
            return True, max(limit - count - 1, 0)
        except Exception:
            # Redis died mid-flight; continue on local fallback (no global flip,
            # a transient error should not permanently disable Redis).
            pass

    entries = [ts for ts in _local.get(key, []) if ts > now - window_seconds]
    if len(entries) >= limit:
        _local[key] = entries
        return False, 0
    entries.append(now)
    _local[key] = entries
    return True, max(limit - len(entries), 0)


def clear(key: str) -> None:
    _local.pop(key, None)
    client = _get_redis()
    if client is not None:
        try:
            client.delete(f"rl:{key}")
        except Exception:
            pass
