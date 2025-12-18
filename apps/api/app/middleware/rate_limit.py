"""
Rate Limiting Middleware
Protects API from abuse and DDoS attacks
"""

import asyncio
import hashlib
import os
import time
from collections import defaultdict
from typing import Dict, Optional, Tuple, Set

import structlog
from redis import asyncio as aioredis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings

logger = structlog.get_logger()

# Development mode - disable rate limiting entirely
DEV_MODE = os.getenv("DEV_MODE", "false").lower() in ("true", "1", "yes")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Production-grade rate limiting with Redis backend.

    Features:
    - Sliding window algorithm
    - Per-user and per-IP limits
    - API key tier-based limits
    - Graceful degradation if Redis unavailable
    - Localhost whitelist for development
    - Path exclusions for public endpoints
    - DEV_MODE flag to disable rate limiting
    """

    # Whitelisted IPs (bypass rate limiting)
    WHITELISTED_IPS: Set[str] = {
        "127.0.0.1",
        "::1",
        "localhost",
        "0.0.0.0",
    }

    # Excluded paths (no rate limiting)
    EXCLUDED_PATHS: Set[str] = {
        "/health",
        "/health/detailed",
        "/health/ready",
        "/ready",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/health",
    }

    # Path prefixes to exclude for GET requests (public API)
    EXCLUDED_PATH_PREFIXES_GET: Set[str] = {
        "/api/v1/marketplace/listings",
        "/api/v1/marketplace/categories",
        "/api/v1/marketplace/featured",
        "/api/v1/marketplace/search",
    }

    # Rate limits per tier (requests per minute)
    # Production-safe defaults - can be overridden via environment
    TIER_LIMITS = {
        "anonymous": 30,      # Unauthenticated users
        "free": 60,           # Free tier users
        "pro": 300,           # Pro tier users
        "enterprise": 1000,   # Enterprise tier users
        "unlimited": float("inf"),
    }

    # Endpoint-specific limits (for sensitive operations)
    # These override tier limits for specific paths
    ENDPOINT_LIMITS = {
        # Authentication - strict limits to prevent brute force
        "/api/v1/auth/login": 5,           # 5 login attempts per minute
        "/api/v1/auth/register": 3,        # 3 registrations per minute
        "/api/v1/auth/forgot-password": 3, # 3 password reset requests per minute
        "/api/v1/auth/reset-password": 5,  # 5 reset attempts per minute
        "/api/v1/auth/refresh": 10,        # 10 token refreshes per minute

        # Identity operations - prevent abuse
        "/api/v1/identity/register": 2,    # 2 identity registrations per minute
        "/api/v1/identity/verify": 100,    # 100 verifications per minute (API usage)

        # Marketplace - prevent automated scraping/purchasing
        "/api/v1/marketplace/license/purchase": 10,  # 10 purchases per minute

        # User account operations
        "/api/v1/users/api-keys": 5,       # 5 API key operations per minute

        # Refunds - strict to prevent abuse
        "/api/v1/refunds/request": 2,      # 2 refund requests per minute

        # Webhooks - allow higher limits for legitimate services
        "/api/v1/webhooks/stripe": 100,    # Stripe sends multiple events
        "/api/v1/webhooks/clerk": 50,      # Clerk user events
        "/api/v1/webhooks/replicate": 50,  # Replicate training callbacks
    }

    def __init__(self, app, redis_url: str = None):
        super().__init__(app)
        self.redis_url = redis_url or settings.REDIS_URL
        self.redis: Optional[aioredis.Redis] = None
        self.local_cache: Dict[str, list] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def get_redis(self) -> Optional[aioredis.Redis]:
        """Get or create Redis connection"""
        if self.redis is None:
            try:
                self.redis = await aioredis.from_url(
                    self.redis_url, encoding="utf-8", decode_responses=True
                )
            except Exception as e:
                logger.warning(f"Redis unavailable for rate limiting: {e}")
                return None
        return self.redis

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _is_whitelisted(self, request: Request) -> bool:
        """Check if client IP is whitelisted"""
        ip = self._get_client_ip(request)
        return ip in self.WHITELISTED_IPS

    def _is_excluded_path(self, request: Request) -> bool:
        """Check if path should be excluded from rate limiting"""
        path = request.url.path

        # Check exact matches
        if path in self.EXCLUDED_PATHS:
            return True

        # Check prefix matches for GET requests
        if request.method == "GET":
            for prefix in self.EXCLUDED_PATH_PREFIXES_GET:
                if path.startswith(prefix):
                    return True

        return False

    def get_client_identifier(self, request: Request) -> Tuple[str, str]:
        """
        Get unique client identifier and tier.
        Returns (identifier, tier)
        """
        # Check for API key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
            return f"apikey:{key_hash}", self._get_api_key_tier(api_key)

        # Check for authenticated user
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            tier = getattr(request.state, "user_tier", "free")
            return f"user:{user_id}", tier

        # Fall back to IP address
        ip = self._get_client_ip(request)
        return f"ip:{ip}", "anonymous"

    def _get_api_key_tier(self, api_key: str) -> str:
        """Get tier for API key (would query database in production)"""
        # Placeholder - in production, cache this from database
        if api_key.startswith("sk_live_"):
            return "pro"
        elif api_key.startswith("sk_enterprise_"):
            return "enterprise"
        return "free"

    def get_limit_for_request(self, request: Request, tier: str) -> int:
        """Get rate limit for this specific request"""
        # Check endpoint-specific limits first
        path = request.url.path
        for endpoint, limit in self.ENDPOINT_LIMITS.items():
            if path.startswith(endpoint):
                return limit

        # Use tier-based limit
        return self.TIER_LIMITS.get(tier, self.TIER_LIMITS["anonymous"])

    async def is_rate_limited_redis(
        self, identifier: str, limit: int, window: int = 60
    ) -> Tuple[bool, int, int]:
        """
        Check rate limit using Redis sliding window.
        Returns (is_limited, remaining, reset_time)
        """
        redis = await self.get_redis()
        if not redis:
            return await self.is_rate_limited_local(identifier, limit, window)

        now = time.time()
        key = f"ratelimit:{identifier}"
        window_start = now - window

        pipe = redis.pipeline()

        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        # Add current request
        pipe.zadd(key, {str(now): now})
        # Count requests in window
        pipe.zcard(key)
        # Set expiry
        pipe.expire(key, window * 2)

        results = await pipe.execute()
        request_count = results[2]

        remaining = max(0, limit - request_count)
        reset_time = int(now + window)

        return request_count > limit, remaining, reset_time

    async def is_rate_limited_local(
        self, identifier: str, limit: int, window: int = 60
    ) -> Tuple[bool, int, int]:
        """Fallback local rate limiting if Redis unavailable"""
        now = time.time()
        window_start = now - window

        async with self._lock:
            # Clean old entries
            self.local_cache[identifier] = [
                ts for ts in self.local_cache[identifier] if ts > window_start
            ]

            # Add current request
            self.local_cache[identifier].append(now)

            request_count = len(self.local_cache[identifier])

        remaining = max(0, limit - request_count)
        reset_time = int(now + window)

        return request_count > limit, remaining, reset_time

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for localhost (direct check)
        client_ip = request.client.host if request.client else "unknown"
        if client_ip in ["127.0.0.1", "::1", "localhost"]:
            return await call_next(request)

        # Skip rate limiting entirely in DEV_MODE
        if DEV_MODE:
            return await call_next(request)

        # Skip rate limiting for whitelisted IPs (localhost)
        if self._is_whitelisted(request):
            return await call_next(request)

        # Skip rate limiting for excluded paths
        if self._is_excluded_path(request):
            return await call_next(request)

        identifier, tier = self.get_client_identifier(request)
        limit = self.get_limit_for_request(request, tier)

        # Check if unlimited
        if limit == float("inf"):
            return await call_next(request)

        is_limited, remaining, reset_time = await self.is_rate_limited_redis(identifier, int(limit))

        # Add rate limit headers to response
        if is_limited:
            logger.warning(
                "Rate limit exceeded", identifier=identifier, tier=tier, path=request.url.path
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please slow down.",
                    "retry_after": reset_time - int(time.time()),
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time - int(time.time())),
                },
            )

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response
