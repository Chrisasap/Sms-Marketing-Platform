"""Redis-based sliding window rate limiter for message sending.

Supports:
- Per-tenant messages-per-second (MPS) limits (set by 10DLC campaign tier)
- Daily message count caps (T-Mobile style)
- Queue depth inspection
"""

import time
import logging

import redis.asyncio as aioredis

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimiter:
    """Sliding-window rate limiter backed by Redis sorted sets."""

    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        """Lazy-initialize the Redis connection."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                settings.redis_url,
                decode_responses=True,
            )
        return self._redis

    async def close(self) -> None:
        """Cleanly shut down the Redis connection pool."""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None

    # ------------------------------------------------------------------
    # Generic sliding-window check
    # ------------------------------------------------------------------

    async def check_rate(
        self,
        key: str,
        max_per_second: int,
        window_seconds: int = 1,
    ) -> bool:
        """Return ``True`` if the action is within the rate limit.

        Uses a Redis sorted set where each member is a timestamp and the
        score is the same timestamp.  Entries older than the window are
        pruned on every call.
        """
        r = await self._get_redis()
        now = time.time()
        window_start = now - window_seconds

        pipe = r.pipeline()
        # Prune expired entries
        pipe.zremrangebyscore(key, 0, window_start)
        # Count remaining entries (== actions in the current window)
        pipe.zcard(key)
        # Tentatively add the new action
        pipe.zadd(key, {str(now): now})
        # Auto-expire the whole key shortly after the window closes
        pipe.expire(key, window_seconds + 1)

        results = await pipe.execute()
        current_count = results[1]

        if current_count >= max_per_second * window_seconds:
            # Over the limit -- remove the entry we speculatively added
            await r.zrem(key, str(now))
            return False

        return True

    # ------------------------------------------------------------------
    # Tenant-level MPS
    # ------------------------------------------------------------------

    async def check_tenant_rate(
        self, tenant_id: str, mps_limit: int
    ) -> bool:
        """Check whether the tenant is within its messages-per-second cap."""
        key = f"rate:tenant:{tenant_id}"
        return await self.check_rate(key, mps_limit)

    # ------------------------------------------------------------------
    # Daily sending cap (carrier-imposed, e.g. T-Mobile)
    # ------------------------------------------------------------------

    async def check_daily_limit(
        self, tenant_id: str, daily_limit: int
    ) -> bool:
        """Return ``True`` if the tenant has not exceeded its daily cap."""
        r = await self._get_redis()
        key = f"daily:tenant:{tenant_id}"
        count = await r.get(key)
        if count is not None and int(count) >= daily_limit:
            return False
        return True

    async def increment_daily_count(self, tenant_id: str) -> int:
        """Increment and return the tenant's daily message count."""
        r = await self._get_redis()
        key = f"daily:tenant:{tenant_id}"
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, 86400)  # 24-hour TTL
        results = await pipe.execute()
        return int(results[0])

    async def get_daily_count(self, tenant_id: str) -> int:
        """Return the current daily message count for a tenant."""
        r = await self._get_redis()
        key = f"daily:tenant:{tenant_id}"
        count = await r.get(key)
        return int(count) if count else 0

    # ------------------------------------------------------------------
    # Queue depth (informational)
    # ------------------------------------------------------------------

    async def get_queue_depth(self, tenant_id: str) -> int:
        """Return the number of messages sitting in the tenant's send queue."""
        r = await self._get_redis()
        key = f"queue:tenant:{tenant_id}"
        return await r.llen(key)

    # ------------------------------------------------------------------
    # Per-number rate limiting
    # ------------------------------------------------------------------

    async def check_number_rate(
        self, phone_number: str, mps_limit: int
    ) -> bool:
        """Per-number MPS check (useful for shared short codes)."""
        key = f"rate:number:{phone_number}"
        return await self.check_rate(key, mps_limit)


# ---------------------------------------------------------------------------
# Singleton -- import and use directly
# ---------------------------------------------------------------------------
rate_limiter = RateLimiter()
