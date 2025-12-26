"""
Rate Limiting Middleware
Protects API from abuse and DDoS attacks with Prometheus metrics
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
from app.core.monitoring import RATE_LIMIT_EXCEEDED, RATE_LIMIT_REQUESTS

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

        # SECURITY FIX: Added missing auth extended endpoints
        "/api/v1/auth/password-reset/request": 3,    # 3 per minute (abuse prevention)
        "/api/v1/auth/password-reset/confirm": 5,    # 5 per minute
        "/api/v1/auth/verify-email/send": 3,         # 3 per minute
        "/api/v1/auth/verify-email/confirm": 10,     # 10 per minute
        "/api/v1/auth/2fa/enable": 5,                # 5 per minute
        "/api/v1/auth/2fa/verify": 10,               # 10 per minute
        "/api/v1/auth/2fa/disable": 3,               # 3 per minute
        "/api/v1/auth/2fa/verify-login": 5,          # 5 per minute (brute force protection)

        # Identity operations - prevent abuse
        "/api/v1/identity/register": 2,    # 2 identity registrations per minute
        "/api/v1/identity/verify": 100,    # 100 verifications per minute (API usage)

        # Marketplace - prevent automated scraping/purchasing
        "/api/v1/marketplace/license/purchase": 10,  # 10 purchases per minute

        # User account operations
        "/api/v1/users/api-keys": 5,       # 5 API key operations per minute

        # SECURITY FIX: Added GDPR sensitive operations (strict limits)
        "/api/v1/gdpr/export": 1,          # 1 per minute (resource intensive)
        "/api/v1/gdpr/delete-account": 1,  # 1 per minute (destructive operation)

        # SECURITY FIX: Added resource-intensive operations
        "/api/v1/actor-packs/train": 2,    # 2 per minute (GPU intensive)
        "/api/v1/analytics/dashboard": 10, # 10 per minute (database intensive)
        "/api/v1/admin/dashboard": 10,     # 10 per minute (database intensive)

        # Subscription operations
        "/api/v1/subscriptions/checkout": 5,   # 5 per minute
        "/api/v1/subscriptions/cancel": 2,     # 2 per minute
        "/api/v1/subscriptions/reactivate": 2, # 2 per minute

        # Refunds - strict to prevent abuse
        "/api/v1/refunds/request": 2,      # 2 refund requests per minute

        # Webhooks - allow higher limits for legitimate services
        "/api/v1/webhooks/stripe": 100,    # Stripe sends multiple events
        "/api/v1/webhooks/clerk": 50,      # Clerk user events
        "/api/v1/webhooks/replicate": 50,  # Replicate training callbacks

        # OAuth - moderate limits to prevent abuse
        "/api/v1/oauth/google/authorize": 10,   # 10 per minute
        "/api/v1/oauth/github/authorize": 10,   # 10 per minute
        "/api/v1/oauth/google/callback": 10,    # 10 per minute
        "/api/v1/oauth/github/callback": 10,    # 10 per minute

        # FILE UPLOADS - strict limits to prevent disk abuse
        "/api/v1/identity/register": 3,         # 3 uploads per minute (face + selfie)
        "/api/v1/actor-packs/upload": 5,        # 5 uploads per minute
        "/api/v1/actor-packs/training-images": 10,  # 10 image uploads per minute
        "/api/v1/users/avatar": 5,              # 5 avatar uploads per minute
    }

    # Per-user daily upload quota (in MB)
    DAILY_UPLOAD_QUOTA_MB = {
        "anonymous": 0,       # No uploads for anonymous
        "free": 100,          # 100MB per day
        "pro": 1000,          # 1GB per day
        "enterprise": 10000,  # 10GB per day
        "unlimited": float("inf"),
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

        # Check for authenticated user from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            tier = getattr(request.state, "user_tier", "free")
            return f"user:{user_id}", tier

        # CRITICAL FIX: Try to extract user from JWT token in Authorization header
        # This runs before the auth dependency, so we need to peek at the token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                token = auth_header[7:]
                # Decode without verification just to get user_id for rate limiting
                # Full verification happens in the auth dependency
                import jwt
                payload = jwt.decode(token, options={"verify_signature": False})
                user_id = payload.get("sub")
                tier = payload.get("tier", "free")
                if user_id:
                    return f"user:{user_id}", tier
            except Exception:
                pass  # Invalid token, fall back to IP

        # Fall back to IP address
        ip = self._get_client_ip(request)
        return f"ip:{ip}", "anonymous"

    async def _get_api_key_tier_async(self, api_key: str) -> str:
        """
        Get tier for API key from cache or database.

        CRITICAL FIX: Now properly looks up API key tier from Redis cache.
        Falls back to prefix-based detection if cache unavailable.
        """
        try:
            from app.services.cache import cache

            # Try to get tier from cache first
            cache_key = f"apikey_tier:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"
            if cache.is_available:
                cached_tier = await cache.get(cache_key)
                if cached_tier:
                    return cached_tier
        except Exception:
            pass

        # Fallback: Use prefix-based detection
        # In production, this should query the database
        if api_key.startswith("sk_enterprise_"):
            return "enterprise"
        elif api_key.startswith("sk_live_"):
            return "pro"
        return "free"

    def _get_api_key_tier(self, api_key: str) -> str:
        """Sync wrapper for backwards compatibility"""
        # Use prefix-based detection for sync context
        if api_key.startswith("sk_enterprise_"):
            return "enterprise"
        elif api_key.startswith("sk_live_"):
            return "pro"
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

        # Extract identifier type for metrics
        identifier_type = identifier.split(":")[0] if ":" in identifier else "unknown"
        path = request.url.path

        # Add rate limit headers to response
        if is_limited:
            # Record rate limit exceeded metric
            RATE_LIMIT_EXCEEDED.labels(
                endpoint=path,
                tier=tier,
                identifier_type=identifier_type
            ).inc()

            RATE_LIMIT_REQUESTS.labels(
                endpoint=path,
                tier=tier,
                allowed="false"
            ).inc()

            logger.warning(
                "Rate limit exceeded",
                identifier=identifier,
                tier=tier,
                path=path,
                identifier_type=identifier_type
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

        # Record allowed request metric
        RATE_LIMIT_REQUESTS.labels(
            endpoint=path,
            tier=tier,
            allowed="true"
        ).inc()

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response
