"""
Redis Cache Service

Enterprise-grade caching layer with:
- Automatic serialization/deserialization
- TTL management
- Cache invalidation patterns
- Connection pooling
- Fallback handling
- Timeout configuration
- Retry logic for transient failures
"""

import asyncio
import hashlib
import json
import time
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, Union

import structlog
from redis import asyncio as aioredis
from redis.exceptions import RedisError, TimeoutError as RedisTimeoutError

from app.core.config import settings

logger = structlog.get_logger()

T = TypeVar("T")

# Timeout configuration
REDIS_CONNECT_TIMEOUT = 5.0  # Connection timeout in seconds
REDIS_SOCKET_TIMEOUT = 2.0  # Operation timeout in seconds
REDIS_RETRY_ATTEMPTS = 3
REDIS_RETRY_DELAY = 0.5  # Base delay for retries


class CacheService:
    """Redis-based caching service with resilience patterns"""

    _instance: Optional["CacheService"] = None
    _redis: Optional[aioredis.Redis] = None
    _connection_attempts: int = 0
    _last_connection_error: Optional[str] = None

    def __new__(cls) -> "CacheService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self) -> None:
        """Initialize Redis connection with retry logic"""
        if self._redis is not None:
            return

        last_error = None
        for attempt in range(1, REDIS_RETRY_ATTEMPTS + 1):
            try:
                self._redis = await aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=20,
                    socket_connect_timeout=REDIS_CONNECT_TIMEOUT,
                    socket_timeout=REDIS_SOCKET_TIMEOUT,
                    retry_on_timeout=True,
                )
                # Verify connection with timeout
                await asyncio.wait_for(self._redis.ping(), timeout=REDIS_CONNECT_TIMEOUT)
                self._connection_attempts = attempt
                logger.info(
                    "Cache service connected to Redis",
                    attempt=attempt,
                    timeout_config={
                        "connect": REDIS_CONNECT_TIMEOUT,
                        "socket": REDIS_SOCKET_TIMEOUT,
                    },
                )
                return
            except (RedisError, asyncio.TimeoutError, OSError) as e:
                last_error = e
                self._last_connection_error = str(e)
                logger.warning(
                    f"Redis connection attempt {attempt}/{REDIS_RETRY_ATTEMPTS} failed",
                    error=str(e),
                )
                if attempt < REDIS_RETRY_ATTEMPTS:
                    await asyncio.sleep(REDIS_RETRY_DELAY * attempt)

        logger.warning(
            "Redis connection failed after all retries, caching disabled",
            error=str(last_error),
            attempts=REDIS_RETRY_ATTEMPTS,
        )
        self._redis = None

    async def close(self) -> None:
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            self._redis = None

    @property
    def is_available(self) -> bool:
        """Check if cache is available"""
        return self._redis is not None

    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        if not self._redis:
            return default
        try:
            value = await self._redis.get(key)
            if value is None:
                return default
            return json.loads(value)
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning("Cache get failed", key=key, error=str(e))
            return default

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set value in cache with optional TTL (seconds)"""
        if not self._redis:
            return False
        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                await self._redis.setex(key, ttl, serialized)
            else:
                await self._redis.set(key, serialized)
            return True
        except (RedisError, TypeError) as e:
            logger.warning("Cache set failed", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self._redis:
            return False
        try:
            await self._redis.delete(key)
            return True
        except RedisError as e:
            logger.warning("Cache delete failed", key=key, error=str(e))
            return False

    async def delete_pattern(self, pattern: str, batch_size: int = 100, max_keys: int = 10000) -> int:
        """
        Delete all keys matching pattern with batching and limits.

        HIGH FIX: Added batching and max_keys limit to prevent timeout on large keysets.
        Uses SCAN with count hint for efficient iteration.
        """
        if not self._redis:
            return 0
        try:
            deleted_count = 0
            keys_processed = 0

            # Use SCAN with count hint for batching
            async for key in self._redis.scan_iter(match=pattern, count=batch_size):
                keys_processed += 1

                # Safety limit to prevent runaway deletion
                if keys_processed > max_keys:
                    logger.warning(
                        "Cache delete_pattern hit max_keys limit",
                        pattern=pattern,
                        max_keys=max_keys,
                        deleted=deleted_count,
                    )
                    break

                # Delete in batches for efficiency
                try:
                    result = await asyncio.wait_for(
                        self._redis.delete(key),
                        timeout=REDIS_SOCKET_TIMEOUT
                    )
                    deleted_count += result
                except asyncio.TimeoutError:
                    logger.warning("Cache delete timeout for key", key=key[:50])
                    continue

            return deleted_count
        except RedisError as e:
            logger.warning("Cache delete pattern failed", pattern=pattern, error=str(e))
            return 0
        except asyncio.TimeoutError:
            logger.warning("Cache delete_pattern scan timeout", pattern=pattern)
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self._redis:
            return False
        try:
            return await self._redis.exists(key) > 0
        except RedisError:
            return False

    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment a counter"""
        if not self._redis:
            return 0
        try:
            return await self._redis.incrby(key, amount)
        except RedisError:
            return 0

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl: Optional[int] = None,
    ) -> Any:
        """Get from cache or compute and store"""
        value = await self.get(key)
        if value is not None:
            return value

        # Compute value
        if callable(factory):
            value = factory()
            if hasattr(value, "__await__"):
                value = await value

        await self.set(key, value, ttl)
        return value


# Global cache instance
cache = CacheService()


# Cache key generators
class CacheKeys:
    """Standard cache key patterns"""

    @staticmethod
    def user(user_id: str) -> str:
        return f"user:{user_id}"

    @staticmethod
    def user_dashboard(user_id: str) -> str:
        return f"user:{user_id}:dashboard"

    @staticmethod
    def identity(identity_id: str) -> str:
        return f"identity:{identity_id}"

    @staticmethod
    def listing(listing_id: str) -> str:
        return f"listing:{listing_id}"

    @staticmethod
    def listings_search(query_hash: str) -> str:
        return f"listings:search:{query_hash}"

    @staticmethod
    def api_key(key_hash: str) -> str:
        return f"apikey:{key_hash}"

    @staticmethod
    def rate_limit(identifier: str, window: str) -> str:
        return f"ratelimit:{identifier}:{window}"


# Cache TTL constants (in seconds)
class CacheTTL:
    """Standard cache TTL values"""

    SHORT = 60  # 1 minute
    MEDIUM = 300  # 5 minutes
    LONG = 3600  # 1 hour
    DAY = 86400  # 24 hours
    WEEK = 604800  # 7 days


def cached(
    key_prefix: str,
    ttl: int = CacheTTL.MEDIUM,
    key_builder: Optional[Callable[..., str]] = None,
):
    """
    Decorator for caching function results.

    Usage:
        @cached("user_profile", ttl=300)
        async def get_user_profile(user_id: str):
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Build cache key
            if key_builder:
                cache_key = f"{key_prefix}:{key_builder(*args, **kwargs)}"
            else:
                # Generate key from args
                key_parts = [str(arg) for arg in args]
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                key_hash = hashlib.md5(":".join(key_parts).encode()).hexdigest()[:12]
                cache_key = f"{key_prefix}:{key_hash}"

            # Try to get from cache
            if cache.is_available:
                cached_value = await cache.get(cache_key)
                if cached_value is not None:
                    logger.debug("Cache hit", key=cache_key)
                    return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            if cache.is_available and result is not None:
                await cache.set(cache_key, result, ttl)
                logger.debug("Cache set", key=cache_key, ttl=ttl)

            return result

        return wrapper

    return decorator


async def invalidate_user_cache(user_id: str) -> None:
    """Invalidate all cache entries for a user"""
    await cache.delete_pattern(f"user:{user_id}:*")


async def invalidate_identity_cache(identity_id: str) -> None:
    """Invalidate all cache entries for an identity"""
    await cache.delete(CacheKeys.identity(identity_id))
    await cache.delete_pattern("listings:search:*")


async def invalidate_listing_cache(listing_id: str) -> None:
    """Invalidate listing and search caches"""
    await cache.delete(CacheKeys.listing(listing_id))
    await cache.delete_pattern("listings:search:*")
