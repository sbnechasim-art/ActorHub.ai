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

DB_POOL_SIZE = Gauge("db_connection_pool_size", "Database connection pool size")


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


async def check_database_health() -> dict:
    """Check database connectivity"""
    from sqlalchemy import text

    from app.core.database import async_session_maker

    try:
        start = time.time()
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        latency = time.time() - start

        return {"status": "healthy", "latency_ms": round(latency * 1000, 2)}
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
