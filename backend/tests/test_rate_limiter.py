"""Tests for app.services.rate_limiter -- Redis-based sliding window rate limiter."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.rate_limiter import RateLimiter


# ===========================================================================
# Helpers
# ===========================================================================


def _make_rate_limiter_with_mock_redis(mock_redis) -> RateLimiter:
    """Create a RateLimiter instance pre-loaded with a mock Redis client."""
    limiter = RateLimiter()
    limiter._redis = mock_redis
    return limiter


def _make_pipeline_mock(current_count: int = 0):
    """Create a mock Redis pipeline that reports a given current count.

    Note: redis-py's pipeline() is a *synchronous* method that returns
    a pipeline object, so we use MagicMock (not AsyncMock) for it.
    The pipeline's execute() *is* async.
    """
    pipe = MagicMock()
    # All chained methods return the pipe itself for method chaining
    pipe.zremrangebyscore = MagicMock(return_value=pipe)
    pipe.zcard = MagicMock(return_value=pipe)
    pipe.zadd = MagicMock(return_value=pipe)
    pipe.expire = MagicMock(return_value=pipe)
    pipe.incr = MagicMock(return_value=pipe)
    # execute returns: [zremrangebyscore_result, zcard_result, zadd_result, expire_result]
    pipe.execute = AsyncMock(return_value=[0, current_count, True, True])
    return pipe


def _make_redis_mock_with_pipeline(current_count: int = 0):
    """Create a mock Redis client where pipeline() is synchronous."""
    mock_redis = AsyncMock()
    pipe = _make_pipeline_mock(current_count)
    # pipeline() is synchronous in redis-py, returns the pipe directly
    mock_redis.pipeline = MagicMock(return_value=pipe)
    mock_redis.zrem = AsyncMock(return_value=1)
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.llen = AsyncMock(return_value=0)
    mock_redis.close = AsyncMock()
    return mock_redis, pipe


# ===========================================================================
# check_rate (generic sliding window)
# ===========================================================================


class TestCheckRate:
    """Tests for RateLimiter.check_rate."""

    @pytest.mark.asyncio
    async def test_check_rate_allows_under_limit(self, override_settings):
        """When the current count is below the limit, should return True."""
        mock_redis, pipe = _make_redis_mock_with_pipeline(current_count=3)

        limiter = _make_rate_limiter_with_mock_redis(mock_redis)
        result = await limiter.check_rate("rate:test", max_per_second=10)

        assert result is True
        # Pipeline should have been executed
        pipe.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_check_rate_blocks_over_limit(self, override_settings):
        """When the current count meets/exceeds the limit, should return False
        and remove the speculatively added entry."""
        mock_redis, pipe = _make_redis_mock_with_pipeline(current_count=10)

        limiter = _make_rate_limiter_with_mock_redis(mock_redis)
        result = await limiter.check_rate("rate:test", max_per_second=10)

        assert result is False
        # Should have called zrem to remove the speculative entry
        mock_redis.zrem.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_check_rate_exactly_at_limit(self, override_settings):
        """When count equals max_per_second * window_seconds, should block."""
        mock_redis, pipe = _make_redis_mock_with_pipeline(current_count=5)

        limiter = _make_rate_limiter_with_mock_redis(mock_redis)
        # 5 >= 5*1 -> blocked
        result = await limiter.check_rate("rate:test", max_per_second=5, window_seconds=1)

        assert result is False

    @pytest.mark.asyncio
    async def test_check_rate_custom_window(self, override_settings):
        """A wider window should scale the allowed count."""
        mock_redis, pipe = _make_redis_mock_with_pipeline(current_count=15)

        limiter = _make_rate_limiter_with_mock_redis(mock_redis)
        result = await limiter.check_rate("rate:test", max_per_second=10, window_seconds=2)

        assert result is True  # 15 < 20


# ===========================================================================
# check_tenant_rate
# ===========================================================================


class TestCheckTenantRate:
    """Tests for check_tenant_rate (wrapper around check_rate)."""

    @pytest.mark.asyncio
    async def test_check_tenant_rate_uses_correct_key(self, override_settings):
        """check_tenant_rate should call check_rate with the tenant-scoped key."""
        limiter = RateLimiter()
        limiter.check_rate = AsyncMock(return_value=True)

        result = await limiter.check_tenant_rate("tenant-123", mps_limit=30)

        assert result is True
        limiter.check_rate.assert_awaited_once_with("rate:tenant:tenant-123", 30)


# ===========================================================================
# Daily limits
# ===========================================================================


class TestDailyLimit:
    """Tests for check_daily_limit / increment_daily_count."""

    @pytest.mark.asyncio
    async def test_check_daily_limit_allows(self, override_settings):
        """When the daily count is below the limit, should return True."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="500")

        limiter = _make_rate_limiter_with_mock_redis(mock_redis)
        result = await limiter.check_daily_limit("tenant-abc", daily_limit=1000)

        assert result is True

    @pytest.mark.asyncio
    async def test_check_daily_limit_blocks(self, override_settings):
        """When the daily count meets the limit, should return False."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="1000")

        limiter = _make_rate_limiter_with_mock_redis(mock_redis)
        result = await limiter.check_daily_limit("tenant-abc", daily_limit=1000)

        assert result is False

    @pytest.mark.asyncio
    async def test_check_daily_limit_no_key(self, override_settings):
        """When the Redis key doesn't exist yet (None), should return True."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        limiter = _make_rate_limiter_with_mock_redis(mock_redis)
        result = await limiter.check_daily_limit("tenant-new", daily_limit=500)

        assert result is True

    @pytest.mark.asyncio
    async def test_check_daily_limit_over(self, override_settings):
        """When the daily count exceeds the limit, should return False."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="1500")

        limiter = _make_rate_limiter_with_mock_redis(mock_redis)
        result = await limiter.check_daily_limit("tenant-over", daily_limit=1000)

        assert result is False


# ===========================================================================
# increment_daily_count
# ===========================================================================


class TestIncrementDailyCount:
    """Tests for increment_daily_count."""

    @pytest.mark.asyncio
    async def test_increment_daily_count(self, override_settings):
        """increment_daily_count should INCR the key and set a 24-hour TTL."""
        mock_redis = AsyncMock()
        pipe = MagicMock()
        pipe.incr = MagicMock(return_value=pipe)
        pipe.expire = MagicMock(return_value=pipe)
        pipe.execute = AsyncMock(return_value=[42, True])
        mock_redis.pipeline = MagicMock(return_value=pipe)

        limiter = _make_rate_limiter_with_mock_redis(mock_redis)
        count = await limiter.increment_daily_count("tenant-xyz")

        assert count == 42
        pipe.incr.assert_called_once_with("daily:tenant:tenant-xyz")
        pipe.expire.assert_called_once_with("daily:tenant:tenant-xyz", 86400)

    @pytest.mark.asyncio
    async def test_increment_daily_count_first_message(self, override_settings):
        """First increment should return 1."""
        mock_redis = AsyncMock()
        pipe = MagicMock()
        pipe.incr = MagicMock(return_value=pipe)
        pipe.expire = MagicMock(return_value=pipe)
        pipe.execute = AsyncMock(return_value=[1, True])
        mock_redis.pipeline = MagicMock(return_value=pipe)

        limiter = _make_rate_limiter_with_mock_redis(mock_redis)
        count = await limiter.increment_daily_count("tenant-first")

        assert count == 1


# ===========================================================================
# get_daily_count
# ===========================================================================


class TestGetDailyCount:
    """Tests for get_daily_count."""

    @pytest.mark.asyncio
    async def test_get_daily_count_existing(self, override_settings):
        """Should return the integer count from Redis."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="99")

        limiter = _make_rate_limiter_with_mock_redis(mock_redis)
        count = await limiter.get_daily_count("tenant-99")

        assert count == 99

    @pytest.mark.asyncio
    async def test_get_daily_count_no_key(self, override_settings):
        """Should return 0 if the key doesn't exist."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        limiter = _make_rate_limiter_with_mock_redis(mock_redis)
        count = await limiter.get_daily_count("tenant-none")

        assert count == 0


# ===========================================================================
# Connection management
# ===========================================================================


class TestConnectionManagement:
    """Tests for lazy init and close."""

    @pytest.mark.asyncio
    async def test_lazy_redis_init(self, override_settings):
        """_get_redis should create a connection on first call."""
        limiter = RateLimiter()
        assert limiter._redis is None

        with patch("app.services.rate_limiter.aioredis.from_url") as mock_from_url:
            mock_conn = AsyncMock()
            mock_from_url.return_value = mock_conn

            r = await limiter._get_redis()
            assert r is mock_conn
            mock_from_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_cleans_up(self, override_settings):
        """close() should close the Redis connection and reset the reference."""
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()

        limiter = _make_rate_limiter_with_mock_redis(mock_redis)
        await limiter.close()

        mock_redis.close.assert_awaited_once()
        assert limiter._redis is None

    @pytest.mark.asyncio
    async def test_close_when_not_connected(self, override_settings):
        """close() should be safe to call when not connected."""
        limiter = RateLimiter()
        await limiter.close()  # Should not raise


# ===========================================================================
# Queue depth
# ===========================================================================


class TestQueueDepth:
    """Tests for get_queue_depth."""

    @pytest.mark.asyncio
    async def test_get_queue_depth(self, override_settings):
        """Should return the list length from Redis."""
        mock_redis = AsyncMock()
        mock_redis.llen = AsyncMock(return_value=25)

        limiter = _make_rate_limiter_with_mock_redis(mock_redis)
        depth = await limiter.get_queue_depth("tenant-q")

        assert depth == 25
        mock_redis.llen.assert_awaited_once_with("queue:tenant:tenant-q")

    @pytest.mark.asyncio
    async def test_get_queue_depth_empty(self, override_settings):
        """An empty queue should return 0."""
        mock_redis = AsyncMock()
        mock_redis.llen = AsyncMock(return_value=0)

        limiter = _make_rate_limiter_with_mock_redis(mock_redis)
        depth = await limiter.get_queue_depth("tenant-empty")

        assert depth == 0
