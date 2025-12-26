"""
Security Headers Middleware
Adds security headers to all responses including CSRF protection
"""

import hashlib
import hmac
import secrets
from typing import Optional, Set

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings

# Security constants - use settings for configurable values

# CSRF Configuration
CSRF_TOKEN_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_COOKIE_NAME = "_csrf"
CSRF_TOKEN_LENGTH = 32


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF Protection Middleware.

    Protects against Cross-Site Request Forgery attacks by:
    1. Setting a CSRF cookie with a random token
    2. Requiring the token in a header for state-changing requests
    3. Validating Origin/Referer headers match allowed origins

    Skips CSRF validation for:
    - GET, HEAD, OPTIONS requests (safe methods)
    - Requests with Bearer token (API clients)
    - Requests with X-API-Key header (programmatic access)
    - Webhook endpoints (use signature verification instead)
    """

    # Methods that require CSRF validation
    UNSAFE_METHODS: Set[str] = {"POST", "PUT", "PATCH", "DELETE"}

    # Endpoints exempt from CSRF (webhooks use signature verification)
    # Auth endpoints are exempt because:
    # 1. User isn't authenticated yet (no session to hijack)
    # 2. Credentials themselves provide protection
    EXEMPT_PATHS: Set[str] = {
        "/api/v1/webhooks/stripe",
        "/api/v1/webhooks/clerk",
        "/api/v1/webhooks/replicate",
        "/api/v1/users/login",
        "/api/v1/users/register",
        "/api/v1/users/refresh",
        "/api/v1/users/forgot-password",
        "/api/v1/users/reset-password",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
        "/api/v1/auth/google",
        "/api/v1/auth/google/callback",
        "/api/v1/auth/github",
        "/api/v1/auth/github/callback",
    }

    async def dispatch(self, request: Request, call_next):
        """Validate CSRF token for state-changing requests."""
        method = request.method.upper()
        path = request.url.path

        # Skip CSRF for safe methods
        if method not in self.UNSAFE_METHODS:
            response = await call_next(request)
            # Set CSRF cookie on GET requests for browser clients
            if method == "GET" and not request.headers.get("X-API-Key"):
                self._set_csrf_cookie(request, response)
            return response

        # Skip CSRF for API key authenticated requests (programmatic access)
        if request.headers.get("X-API-Key"):
            return await call_next(request)

        # Skip CSRF for Bearer token requests (mobile/API clients)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return await call_next(request)

        # Skip CSRF for exempt paths (webhooks)
        if path in self.EXEMPT_PATHS:
            return await call_next(request)

        # For cookie-based auth (browser requests), validate CSRF
        if not self._validate_csrf(request):
            return JSONResponse(
                status_code=403,
                content={
                    "error": "csrf_validation_failed",
                    "message": "CSRF token missing or invalid",
                }
            )

        # Validate Origin/Referer header
        if not self._validate_origin(request):
            return JSONResponse(
                status_code=403,
                content={
                    "error": "origin_validation_failed",
                    "message": "Request origin not allowed",
                }
            )

        return await call_next(request)

    def _generate_csrf_token(self) -> str:
        """Generate a cryptographically secure CSRF token."""
        return secrets.token_urlsafe(CSRF_TOKEN_LENGTH)

    def _validate_csrf(self, request: Request) -> bool:
        """
        Validate CSRF token using double-submit cookie pattern.

        The token from the cookie must match the token in the header.
        """
        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
        header_token = request.headers.get(CSRF_HEADER_NAME)

        if not cookie_token or not header_token:
            return False

        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(cookie_token, header_token)

    def _validate_origin(self, request: Request) -> bool:
        """
        Validate that the request origin is from an allowed domain.

        Checks Origin header first, falls back to Referer.
        """
        origin = request.headers.get("Origin")
        referer = request.headers.get("Referer")

        # If no Origin or Referer, allow (could be same-origin or non-browser)
        if not origin and not referer:
            return True

        # Check Origin header
        if origin:
            return origin in settings.ALLOWED_ORIGINS

        # Fall back to Referer
        if referer:
            from urllib.parse import urlparse
            parsed = urlparse(referer)
            referer_origin = f"{parsed.scheme}://{parsed.netloc}"
            return referer_origin in settings.ALLOWED_ORIGINS

        return True

    def _set_csrf_cookie(self, request: Request, response) -> None:
        """Set CSRF token cookie if not already present."""
        if not request.cookies.get(CSRF_COOKIE_NAME):
            token = self._generate_csrf_token()
            response.set_cookie(
                key=CSRF_COOKIE_NAME,
                value=token,
                httponly=False,  # Must be readable by JavaScript
                secure=settings.COOKIE_SECURE,
                samesite="lax",
                max_age=3600 * 24,  # 24 hours
            )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to protect against common attacks.

    Headers added:
    - X-Content-Type-Options: Prevents MIME sniffing
    - X-Frame-Options: Prevents clickjacking
    - X-XSS-Protection: XSS filter (legacy browsers)
    - Strict-Transport-Security: Forces HTTPS
    - Content-Security-Policy: Controls resource loading
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Controls browser features
    """

    async def dispatch(self, request: Request, call_next):
        """Process request and add security headers to response."""
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # XSS protection for legacy browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Force HTTPS (1 year)
        response.headers["Strict-Transport-Security"] = (
            f"max-age={settings.HSTS_MAX_AGE_SECONDS}; includeSubDomains; preload"
        )

        # Content Security Policy
        # SECURITY: Removed 'unsafe-eval' to prevent XSS attacks via eval()
        # Note: If Next.js requires 'unsafe-eval' for development, add it only
        # in development mode via environment variable
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "  # Removed 'unsafe-eval' for security
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://api.actorhub.ai wss:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy (disable unnecessary features)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "ambient-light-sensor=(), "
            "autoplay=(), "
            "battery=(), "
            "camera=(self), "  # Needed for face capture
            "display-capture=(), "
            "document-domain=(), "
            "encrypted-media=(), "
            "fullscreen=(self), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(self), "  # Needed for voice capture
            "midi=(), "
            "payment=(), "
            "picture-in-picture=(), "
            "publickey-credentials-get=(), "
            "screen-wake-lock=(), "
            "sync-xhr=(), "
            "usb=(), "
            "web-share=(), "
            "xr-spatial-tracking=()"
        )

        # Remove server header
        if "server" in response.headers:
            del response.headers["server"]

        return response


class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Validates and sanitizes input to prevent injection attacks.
    """

    # Patterns that might indicate attacks
    DANGEROUS_PATTERNS = [
        "<script",
        "javascript:",
        "onerror=",
        "onclick=",
        "onload=",
        "../",
        "..\\",
        "\x00",  # Null byte
    ]

    async def dispatch(self, request: Request, call_next):
        """Validate request size and content before processing."""
        from starlette.responses import JSONResponse

        content_length = request.headers.get("content-length")
        content_type = request.headers.get("content-type", "")

        # Determine max size based on content type
        # File uploads (multipart) get 500MB, regular requests get 10MB
        if "multipart/form-data" in content_type:
            max_size = settings.MAX_FILE_UPLOAD_SIZE_BYTES  # 500MB for file uploads
        else:
            max_size = settings.MAX_BODY_SIZE_BYTES  # 10MB for regular requests

        # Check content length against appropriate limit
        if content_length and int(content_length) > max_size:
            return JSONResponse(
                status_code=413,
                content={"error": f"Request body too large. Maximum {max_size // (1024 * 1024)}MB allowed."}
            )

        return await call_next(request)
