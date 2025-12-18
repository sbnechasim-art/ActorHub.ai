"""
Health Check Endpoints

Provides health monitoring for:
- Kubernetes probes (liveness/readiness)
- Load balancer health checks
- Monitoring dashboards
- Operational debugging
"""

from fastapi import APIRouter, Query, Response

from app.core.config import settings
from app.core.monitoring import get_health_status

router = APIRouter()


@router.get("")
async def health_check():
    """
    Basic health check.
    Returns 200 if the service is running.

    Use this for simple load balancer health checks.
    """
    return {"status": "ok", "version": settings.APP_VERSION}


@router.get("/ready")
async def readiness_check(
    include_external: bool = Query(
        False,
        description="Include external API checks (Stripe, Replicate, SendGrid). Slower but more thorough."
    )
):
    """
    Readiness check - verifies all dependencies are healthy.

    **Use cases:**
    - Kubernetes readiness probe (without include_external)
    - Pre-deployment verification (with include_external=true)
    - Troubleshooting connectivity issues

    **Checks performed:**
    - Database (PostgreSQL)
    - Redis
    - Qdrant (Vector DB)
    - Storage (S3/MinIO)
    - Optional: Stripe, Replicate, SendGrid APIs

    Returns 503 if any core service is unhealthy.
    """
    health = await get_health_status(include_external=include_external)

    if health["status"] == "unhealthy":
        return Response(
            content='{"status": "not ready", "details": ' + str(health).replace("'", '"') + '}',
            status_code=503,
            media_type="application/json"
        )

    return health


@router.get("/live")
async def liveness_check():
    """
    Liveness check - verifies the process is alive.

    **Use for:**
    - Kubernetes liveness probe
    - Simple "is it running" checks

    This check is intentionally lightweight and doesn't
    verify dependencies. Use /ready for dependency checks.
    """
    return {"status": "alive", "version": settings.APP_VERSION}


@router.get("/detailed")
async def detailed_health_check():
    """
    Detailed health check with all services including external APIs.

    **Warning:** This endpoint is slower (~2-5 seconds) as it checks
    all external APIs. Use sparingly and cache results.

    Returns comprehensive status of:
    - Core infrastructure (DB, Redis, Qdrant, Storage)
    - External APIs (Stripe, Replicate, SendGrid)
    - System information
    """
    import platform
    import sys

    health = await get_health_status(include_external=True)

    # Add system info
    health["system"] = {
        "python_version": sys.version.split()[0],
        "platform": platform.system(),
        "debug_mode": settings.DEBUG,
        "features": {
            "marketplace": settings.ENABLE_MARKETPLACE,
            "actor_packs": settings.ENABLE_ACTOR_PACKS,
            "voice_cloning": settings.ENABLE_VOICE_CLONING,
            "blockchain": settings.ENABLE_BLOCKCHAIN,
        },
    }

    return health
