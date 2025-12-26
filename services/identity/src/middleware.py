"""Service middleware."""

import time
from collections import defaultdict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .config import get_settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""

    def __init__(self, app):
        super().__init__(app)
        self.settings = get_settings()
        self.requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/ready", "/metrics"]:
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()

        # Check rate limit
        now = time.time()
        window_start = now - self.settings.rate_limit_window

        # Clean old requests
        self.requests[client_ip] = [
            ts for ts in self.requests[client_ip] if ts > window_start
        ]

        # Check limit
        if len(self.requests[client_ip]) >= self.settings.rate_limit_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": self.settings.rate_limit_window,
                },
                headers={
                    "Retry-After": str(self.settings.rate_limit_window),
                    "X-RateLimit-Limit": str(self.settings.rate_limit_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )

        # Record request
        self.requests[client_ip].append(now)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = self.settings.rate_limit_requests - len(self.requests[client_ip])
        response.headers["X-RateLimit-Limit"] = str(self.settings.rate_limit_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response
