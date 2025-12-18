"""
Request Logging Middleware
Structured logging for all API requests with PII filtering
"""

import re
import time
import uuid
from typing import Any, Callable, Dict

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()


# PII patterns to redact from logs
PII_PATTERNS = {
    # Email addresses
    "email": re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
    # Credit card numbers (basic pattern)
    "credit_card": re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
    # SSN pattern
    "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    # Phone numbers
    "phone": re.compile(r'\b(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
    # JWT tokens
    "jwt": re.compile(r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*'),
    # API keys (common patterns)
    "api_key": re.compile(r'\b(sk_live_|pk_live_|sk_test_|pk_test_|ah_)[a-zA-Z0-9]{20,}\b'),
    # Stripe webhook secrets
    "webhook_secret": re.compile(r'\bwhsec_[a-zA-Z0-9]{20,}\b'),
    # Bearer tokens
    "bearer": re.compile(r'Bearer\s+[a-zA-Z0-9._-]+', re.IGNORECASE),
    # Password field values
    "password": re.compile(r'"password"\s*:\s*"[^"]*"', re.IGNORECASE),
}

# Fields to completely redact
SENSITIVE_FIELDS = {
    'password', 'passwd', 'secret', 'token', 'api_key', 'apikey',
    'authorization', 'auth', 'credential', 'credit_card', 'card_number',
    'cvv', 'ssn', 'social_security', 'bank_account',
}


def sanitize_value(value: Any) -> Any:
    """Sanitize a single value, redacting PII"""
    if not isinstance(value, str):
        return value

    sanitized = value

    # Apply PII pattern redaction
    for pattern_name, pattern in PII_PATTERNS.items():
        sanitized = pattern.sub(f'[REDACTED_{pattern_name.upper()}]', sanitized)

    return sanitized


def sanitize_dict(data: Dict[str, Any], depth: int = 0) -> Dict[str, Any]:
    """Recursively sanitize a dictionary, redacting sensitive fields and PII"""
    if depth > 5:  # Prevent infinite recursion
        return {"_truncated": True}

    sanitized = {}
    for key, value in data.items():
        # Check if field name is sensitive
        if key.lower() in SENSITIVE_FIELDS:
            sanitized[key] = '[REDACTED]'
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value, depth + 1)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_dict(item, depth + 1) if isinstance(item, dict)
                else sanitize_value(item)
                for item in value
            ]
        else:
            sanitized[key] = sanitize_value(value)

    return sanitized


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs all API requests with structured data.

    Logged data:
    - Request ID (for tracing)
    - Method and path
    - Client IP
    - User agent
    - Response status
    - Response time
    - User ID (if authenticated)
    """

    # Paths to exclude from logging
    EXCLUDE_PATHS = {"/health", "/ready", "/metrics", "/favicon.ico"}

    # Headers to redact
    SENSITIVE_HEADERS = {"authorization", "x-api-key", "cookie"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for excluded paths
        if request.url.path in self.EXCLUDE_PATHS:
            return await call_next(request)

        # Generate request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Store request ID in state for access in handlers
        request.state.request_id = request_id

        # Get client IP
        forwarded = request.headers.get("X-Forwarded-For")
        client_ip = (
            forwarded.split(",")[0].strip()
            if forwarded
            else (request.client.host if request.client else "unknown")
        )

        # Start timing
        start_time = time.perf_counter()

        # Log request
        logger.info(
            "request_started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query=str(request.query_params) if request.query_params else None,
            client_ip=client_ip,
            user_agent=request.headers.get("user-agent"),
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error
            duration = time.perf_counter() - start_time
            logger.error(
                "request_error",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                client_ip=client_ip,
                duration_ms=round(duration * 1000, 2),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

        # Calculate duration
        duration = time.perf_counter() - start_time

        # Get user ID if authenticated
        user_id = getattr(request.state, "user_id", None)

        # Log response
        log_level = (
            "info"
            if response.status_code < 400
            else ("warning" if response.status_code < 500 else "error")
        )

        getattr(logger, log_level)(
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
            client_ip=client_ip,
            user_id=user_id,
            response_size=response.headers.get("content-length"),
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{round(duration * 1000, 2)}ms"

        return response


def pii_filter_processor(logger, method_name, event_dict):
    """
    Structlog processor that filters PII from log events.
    Should be added to the processor chain.
    """
    return sanitize_dict(event_dict)


def setup_structlog():
    """Configure structured logging with PII filtering"""
    import logging

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            pii_filter_processor,  # Filter PII before rendering
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# Utility function for other modules
def get_sanitized_logger():
    """Get a logger instance with PII filtering enabled"""
    return structlog.get_logger()
