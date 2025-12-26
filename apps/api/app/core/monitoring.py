"""
Monitoring and Observability
Sentry, Prometheus metrics, and health checks
"""

import time

import sentry_sdk
import structlog
from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.core.config import settings

logger = structlog.get_logger()

# ===========================================
# Prometheus Metrics
# ===========================================

# Request metrics
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Business metrics
IDENTITY_REGISTRATIONS = Counter(
    "identity_registrations_total", "Total identity registrations", ["status", "protection_level"]
)

IDENTITY_VERIFICATIONS = Counter(
    "identity_verifications_total", "Total identity verifications", ["matched", "authorized"]
)

ACTOR_PACK_TRAININGS = Counter(
    "actor_pack_trainings_total", "Total Actor Pack trainings", ["status"]
)

LICENSE_PURCHASES = Counter(
    "license_purchases_total", "Total license purchases", ["tier", "usage_type"]
)

# System metrics
ACTIVE_USERS = Gauge("active_users", "Number of active users")

ACTIVE_TRAININGS = Gauge("active_trainings", "Number of active Actor Pack trainings")

# Database connection pool metrics
DB_POOL_SIZE = Gauge("db_connection_pool_size", "Database connection pool size")
DB_POOL_CHECKED_OUT = Gauge("db_pool_checked_out", "Number of connections currently in use")
DB_POOL_OVERFLOW = Gauge("db_pool_overflow", "Number of overflow connections in use")
DB_POOL_AVAILABLE = Gauge("db_pool_available", "Number of available connections in pool")
DB_POOL_WAIT_SECONDS = Histogram(
    "db_pool_wait_seconds",
    "Time spent waiting for a connection from pool",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0]
)
DB_POOL_EXHAUSTED = Counter(
    "db_pool_exhausted_total",
    "Number of times pool was exhausted (no connections available)"
)

# HIGH FIX: Authentication failure metrics
AUTH_FAILURES = Counter(
    "auth_failures_total",
    "Total authentication failures",
    ["type", "reason"]  # type: jwt, api_key, 2fa; reason: invalid, expired, user_not_found
)

AUTH_SUCCESS = Counter(
    "auth_success_total",
    "Total successful authentications",
    ["type"]  # type: jwt, api_key, 2fa
)

API_KEY_VALIDATIONS = Counter(
    "api_key_validations_total",
    "Total API key validations",
    ["status"]  # status: valid, invalid, expired, not_found
)

# Rate limiting metrics
RATE_LIMIT_EXCEEDED = Counter(
    "rate_limit_exceeded_total",
    "Total rate limit exceeded events",
    ["endpoint", "tier", "identifier_type"]
)

RATE_LIMIT_REQUESTS = Counter(
    "rate_limit_requests_total",
    "Total requests processed by rate limiter",
    ["endpoint", "tier", "allowed"]
)

# Notification delivery metrics
NOTIFICATION_SENT = Counter(
    "notification_sent_total",
    "Total notifications sent",
    ["type", "status"]  # type: email, push, webhook; status: success, failed
)

EMAIL_SENT = Counter(
    "email_sent_total",
    "Total emails sent",
    ["template", "status"]
)

WEBHOOK_DELIVERY = Counter(
    "webhook_delivery_total",
    "Total webhook deliveries",
    ["endpoint", "status"]
)

WEBHOOK_LATENCY = Histogram(
    "webhook_latency_seconds",
    "Webhook delivery latency",
    ["endpoint"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
)

# ===========================================
# Resilience Metrics
# ===========================================

# Circuit breaker metrics
CIRCUIT_BREAKER_STATE = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["service"],
)

CIRCUIT_BREAKER_FAILURES = Counter(
    "circuit_breaker_failures_total",
    "Total circuit breaker failures",
    ["service"],
)

CIRCUIT_BREAKER_SUCCESSES = Counter(
    "circuit_breaker_successes_total",
    "Total circuit breaker successes",
    ["service"],
)

CIRCUIT_BREAKER_REJECTIONS = Counter(
    "circuit_breaker_rejections_total",
    "Total requests rejected by open circuit breaker",
    ["service"],
)

# Retry metrics
RETRY_ATTEMPTS = Counter(
    "retry_attempts_total",
    "Total retry attempts",
    ["service", "operation"],
)

RETRY_SUCCESSES = Counter(
    "retry_successes_total",
    "Total successful retries (after initial failure)",
    ["service", "operation"],
)

RETRY_EXHAUSTED = Counter(
    "retry_exhausted_total",
    "Total operations that exhausted all retries",
    ["service", "operation"],
)

# Timeout metrics
OPERATION_TIMEOUTS = Counter(
    "operation_timeouts_total",
    "Total operation timeouts",
    ["service", "operation"],
)

# External service call metrics
EXTERNAL_SERVICE_LATENCY = Histogram(
    "external_service_latency_seconds",
    "External service call latency",
    ["service", "operation"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

# CRITICAL FIX: Add missing metric used by payments.py
EXTERNAL_CALL_DURATION = Histogram(
    "external_call_duration_seconds",
    "Duration of external API calls (Stripe, etc.)",
    ["service", "operation", "status"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

EXTERNAL_SERVICE_CALLS = Counter(
    "external_service_calls_total",
    "Total external service calls",
    ["service", "operation", "status"],
)


# ===========================================
# Sentry Setup
# ===========================================


def setup_sentry(app: FastAPI) -> None:
    """Initialize Sentry error tracking"""
    if not settings.SENTRY_DSN:
        logger.warning("Sentry DSN not configured, error tracking disabled")
        return

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=f"actorhub-api@{settings.VERSION}",
        traces_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,
        profiles_sample_rate=0.1,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            RedisIntegration(),
            CeleryIntegration(),
        ],
        # Don't send PII
        send_default_pii=False,
        # Filter sensitive data
        before_send=filter_sensitive_data,
    )

    logger.info("Sentry initialized", environment=settings.ENVIRONMENT)


def filter_sensitive_data(event, hint):
    """Filter sensitive data before sending to Sentry"""
    # Remove sensitive headers
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        for sensitive in ["authorization", "x-api-key", "cookie"]:
            if sensitive in headers:
                headers[sensitive] = "[FILTERED]"

    # Remove sensitive body data
    if "request" in event and "data" in event["request"]:
        data = event["request"].get("data", {})
        if isinstance(data, dict):
            for sensitive in ["password", "token", "api_key", "secret"]:
                if sensitive in data:
                    data[sensitive] = "[FILTERED]"

    return event


# ===========================================
# Health Checks
# ===========================================


def update_pool_metrics():
    """
    Update database connection pool metrics.

    Call this periodically or on each request to track pool health.
    Alerts when pool usage exceeds 80% threshold.
    """
    try:
        from app.core.database import engine

        pool = engine.pool
        pool_status = pool.status()

        # Parse pool status: "Pool size: X  Connections in pool: Y checked out: Z"
        # SQLAlchemy pool object provides these directly
        pool_size = pool.size()
        checked_out = pool.checkedout()
        overflow = pool.overflow()
        available = pool_size - checked_out + pool.checkedin()

        # Update Prometheus metrics
        DB_POOL_SIZE.set(pool_size)
        DB_POOL_CHECKED_OUT.set(checked_out)
        DB_POOL_OVERFLOW.set(overflow)
        DB_POOL_AVAILABLE.set(max(0, available))

        # Calculate utilization percentage
        max_connections = pool_size + pool._max_overflow
        utilization = checked_out / max_connections if max_connections > 0 else 0

        # Log warning if pool is getting exhausted (>80% utilization)
        if utilization > 0.8:
            logger.warning(
                "Database connection pool nearing exhaustion",
                pool_size=pool_size,
                checked_out=checked_out,
                overflow=overflow,
                utilization=f"{utilization:.1%}",
                max_connections=max_connections,
            )

        # Track exhaustion events
        if checked_out >= max_connections:
            DB_POOL_EXHAUSTED.inc()
            logger.error(
                "Database connection pool EXHAUSTED",
                pool_size=pool_size,
                checked_out=checked_out,
                overflow=overflow,
            )

        return {
            "pool_size": pool_size,
            "checked_out": checked_out,
            "overflow": overflow,
            "available": available,
            "utilization": utilization,
        }
    except Exception as e:
        logger.error("Failed to update pool metrics", error=str(e))
        return None


async def check_database_health() -> dict:
    """Check database connectivity and pool health"""
    from sqlalchemy import text

    from app.core.database import async_session_maker

    try:
        start = time.time()
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        latency = time.time() - start

        # Also update pool metrics
        pool_stats = update_pool_metrics()

        result = {"status": "healthy", "latency_ms": round(latency * 1000, 2)}
        if pool_stats:
            result["pool"] = pool_stats
            # Mark as degraded if pool utilization is high
            if pool_stats["utilization"] > 0.8:
                result["status"] = "degraded"
                result["warning"] = "Connection pool nearing exhaustion"
        return result
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_redis_health() -> dict:
    """Check Redis connectivity"""
    from redis import asyncio as aioredis

    try:
        start = time.time()
        redis = await aioredis.from_url(settings.REDIS_URL)
        await redis.ping()
        await redis.close()
        latency = time.time() - start

        return {"status": "healthy", "latency_ms": round(latency * 1000, 2)}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_qdrant_health() -> dict:
    """Check Qdrant connectivity"""
    from qdrant_client import QdrantClient

    try:
        start = time.time()
        client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        client.get_collections()
        latency = time.time() - start

        return {"status": "healthy", "latency_ms": round(latency * 1000, 2)}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_storage_health() -> dict:
    """Check S3/MinIO connectivity"""
    import httpx

    try:
        start = time.time()
        # Check if using MinIO (local) or AWS S3
        if settings.S3_ENDPOINT and "localhost" in settings.S3_ENDPOINT:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{settings.S3_ENDPOINT}/minio/health/live")
            latency = time.time() - start
            return {
                "status": "healthy" if response.status_code == 200 else "degraded",
                "latency_ms": round(latency * 1000, 2),
                "provider": "minio",
            }
        else:
            # For AWS S3, just verify we have credentials configured
            import boto3
            start = time.time()
            s3 = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
            )
            s3.list_buckets()
            latency = time.time() - start
            return {
                "status": "healthy",
                "latency_ms": round(latency * 1000, 2),
                "provider": "aws_s3",
            }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_stripe_health() -> dict:
    """Check Stripe API connectivity"""
    if not settings.STRIPE_SECRET_KEY:
        return {"status": "not_configured", "error": "STRIPE_SECRET_KEY not set"}

    try:
        import stripe
        start = time.time()
        stripe.api_key = settings.STRIPE_SECRET_KEY
        # Quick API check - retrieve account info
        stripe.Account.retrieve()
        latency = time.time() - start

        return {
            "status": "healthy",
            "latency_ms": round(latency * 1000, 2),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_replicate_health() -> dict:
    """Check Replicate API connectivity"""
    if not settings.REPLICATE_API_TOKEN:
        return {"status": "not_configured", "error": "REPLICATE_API_TOKEN not set"}

    try:
        import httpx
        start = time.time()
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.replicate.com/v1/models",
                headers={"Authorization": f"Token {settings.REPLICATE_API_TOKEN}"},
            )
        latency = time.time() - start

        return {
            "status": "healthy" if response.status_code == 200 else "degraded",
            "latency_ms": round(latency * 1000, 2),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_sendgrid_health() -> dict:
    """Check SendGrid API connectivity"""
    if not settings.SENDGRID_API_KEY:
        return {"status": "not_configured", "error": "SENDGRID_API_KEY not set"}

    try:
        import httpx
        start = time.time()
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.sendgrid.com/v3/scopes",
                headers={"Authorization": f"Bearer {settings.SENDGRID_API_KEY}"},
            )
        latency = time.time() - start

        return {
            "status": "healthy" if response.status_code == 200 else "degraded",
            "latency_ms": round(latency * 1000, 2),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def get_circuit_breaker_status() -> dict:
    """Get status of all circuit breakers for resilience observability"""
    from app.core.resilience import CircuitState

    # Registry of known circuit breakers - will be populated as they're used
    circuit_breakers = {}

    try:
        # Import services that have circuit breakers
        from app.services.training import _replicate_circuit, _elevenlabs_circuit

        circuit_breakers["replicate"] = _replicate_circuit
        circuit_breakers["elevenlabs"] = _elevenlabs_circuit
    except ImportError:
        pass

    try:
        from app.services.payments import StripeService

        if hasattr(StripeService, "_circuit_breaker"):
            circuit_breakers["stripe"] = StripeService._circuit_breaker
    except ImportError:
        pass

    status = {}
    for name, cb in circuit_breakers.items():
        state_name = cb.state.name if hasattr(cb, "state") else "unknown"
        status[name] = {
            "state": state_name,
            "is_open": cb.is_open if hasattr(cb, "is_open") else False,
            "failure_count": cb._failure_count if hasattr(cb, "_failure_count") else 0,
        }

    return status


async def get_health_status(include_external: bool = False) -> dict:
    """
    Get comprehensive health status.

    Args:
        include_external: If True, also check external APIs (Stripe, Replicate, SendGrid).
                         These checks are slower and should be used sparingly.
    """
    import asyncio

    # Core infrastructure checks (always run)
    core_checks = await asyncio.gather(
        check_database_health(),
        check_redis_health(),
        check_qdrant_health(),
        check_storage_health(),
        return_exceptions=True,
    )

    services = {
        "database": (
            core_checks[0]
            if not isinstance(core_checks[0], Exception)
            else {"status": "error", "error": str(core_checks[0])}
        ),
        "redis": (
            core_checks[1]
            if not isinstance(core_checks[1], Exception)
            else {"status": "error", "error": str(core_checks[1])}
        ),
        "qdrant": (
            core_checks[2]
            if not isinstance(core_checks[2], Exception)
            else {"status": "error", "error": str(core_checks[2])}
        ),
        "storage": (
            core_checks[3]
            if not isinstance(core_checks[3], Exception)
            else {"status": "error", "error": str(core_checks[3])}
        ),
    }

    # External API checks (optional, slower)
    external_services = {}
    if include_external:
        external_checks = await asyncio.gather(
            check_stripe_health(),
            check_replicate_health(),
            check_sendgrid_health(),
            return_exceptions=True,
        )

        external_services = {
            "stripe": (
                external_checks[0]
                if not isinstance(external_checks[0], Exception)
                else {"status": "error", "error": str(external_checks[0])}
            ),
            "replicate": (
                external_checks[1]
                if not isinstance(external_checks[1], Exception)
                else {"status": "error", "error": str(external_checks[1])}
            ),
            "sendgrid": (
                external_checks[2]
                if not isinstance(external_checks[2], Exception)
                else {"status": "error", "error": str(external_checks[2])}
            ),
        }

    # Determine overall status based on core services only
    # External services being down shouldn't mark the system as unhealthy
    core_statuses = [s.get("status") for s in services.values()]
    all_healthy = all(s == "healthy" for s in core_statuses)
    any_unhealthy = any(s == "unhealthy" for s in core_statuses)

    result = {
        "status": "healthy" if all_healthy else ("unhealthy" if any_unhealthy else "degraded"),
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "services": services,
    }

    if include_external:
        result["external_services"] = external_services

    return result


# ===========================================
# Metrics Endpoint
# ===========================================


def setup_metrics_endpoint(app: FastAPI) -> None:
    """Add Prometheus metrics endpoint"""

    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ===========================================
# Request Metrics Middleware
# ===========================================


class MetricsMiddleware:
    """Middleware to collect request metrics"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        path = request.url.path
        method = request.method

        # Skip metrics for health/metrics endpoints
        if path in ["/health", "/ready", "/metrics"]:
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.time() - start_time

            # Record metrics
            REQUEST_COUNT.labels(method=method, endpoint=path, status=status_code).inc()

            REQUEST_LATENCY.labels(method=method, endpoint=path).observe(duration)

            # Update pool metrics periodically (every ~100 requests to avoid overhead)
            # Using a simple sampling approach
            import random
            if random.random() < 0.01:  # ~1% of requests
                update_pool_metrics()
