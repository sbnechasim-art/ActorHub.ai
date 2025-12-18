"""
ActorHub.ai API
Digital Identity Protection & Marketplace Platform
"""

import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1 import router as api_v1_router
from app.core.config import settings
from app.core.database import close_db, init_db
from app.middleware.logging import RequestLoggingMiddleware

# Custom middleware imports
from app.middleware.security import InputValidationMiddleware, SecurityHeadersMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.core.monitoring import setup_metrics_endpoint, MetricsMiddleware

# Initialize rate limiter
# Force reload trigger: 2025-12-16
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# Initialize Sentry if configured
if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
    )

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown"""
    # Startup
    logger.info("Starting ActorHub.ai API", version=settings.APP_VERSION)
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down ActorHub.ai API")
    await close_db()


# Create FastAPI app
app = FastAPI(
    title="ActorHub.ai API",
    description="""
    ## Digital Identity Protection & Marketplace Platform

    ActorHub.ai provides:
    - **Identity Registry**: Register and protect your digital identity
    - **Verification API**: Check if images contain protected identities
    - **Marketplace**: License identities for commercial use
    - **Actor Packs**: Download AI-ready models of licensed identities

    ### Quick Start
    1. Register an identity with `/api/v1/identity/register`
    2. Verify faces with `/api/v1/identity/verify`
    3. Purchase licenses via `/api/v1/license/purchase`
    4. Download Actor Packs with `/api/v1/actor-pack/{id}`
    """,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware - restricted for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-API-Key",
        "X-Request-ID",
    ],
    expose_headers=[
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "X-Request-ID",
    ],
    max_age=3600,  # Cache preflight for 1 hour
)

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Input validation middleware
app.add_middleware(InputValidationMiddleware)

# Request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Rate limiting middleware (Redis-backed with tier support)
app.add_middleware(RateLimitMiddleware)

# Prometheus metrics middleware
app.add_middleware(MetricsMiddleware)

# Setup Prometheus metrics endpoint (/metrics)
setup_metrics_endpoint(app)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    response.headers["X-Process-Time-Ms"] = str(round(process_time, 2))
    return response


# Import standardized response helpers
from app.schemas.response import ErrorCodes, create_error_response


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception", error=str(exc), path=request.url.path, method=request.method
    )
    return JSONResponse(
        status_code=500,
        content=create_error_response(
            code=ErrorCodes.INTERNAL_ERROR,
            message="An unexpected error occurred",
            details={"error": str(exc)} if settings.DEBUG else None,
        ),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Convert HTTPException to standardized error response format"""
    # Map status codes to error codes
    status_to_code = {
        400: ErrorCodes.VALIDATION_ERROR,
        401: ErrorCodes.UNAUTHORIZED,
        403: ErrorCodes.FORBIDDEN,
        404: ErrorCodes.NOT_FOUND,
        409: ErrorCodes.CONFLICT,
        429: ErrorCodes.RATE_LIMITED,
    }
    error_code = status_to_code.get(exc.status_code, ErrorCodes.INTERNAL_ERROR)

    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            code=error_code,
            message=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
        ),
    )


# Mount API routes
app.include_router(api_v1_router, prefix="/api/v1")


# Health check endpoints
@app.get("/", tags=["Status"])
async def root():
    """Root endpoint - API information"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "api": "/api/v1",
    }


@app.get("/health", tags=["Status"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "features": {
            "marketplace": settings.ENABLE_MARKETPLACE,
            "actor_packs": settings.ENABLE_ACTOR_PACKS,
            "voice_cloning": settings.ENABLE_VOICE_CLONING,
            "blockchain": settings.ENABLE_BLOCKCHAIN,
        },
    }


@app.get("/health/ready", tags=["Status"])
async def readiness_check():
    """Readiness check - verify all dependencies"""
    from sqlalchemy import text

    from app.core.database import engine

    checks = {"database": False, "redis": False}

    # Check database
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            checks["database"] = True
    except Exception as e:
        logger.error("Database health check failed", error=str(e))

    # Check Redis
    try:
        import redis.asyncio as redis

        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        checks["redis"] = True
        await r.close()
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))

    all_healthy = all(checks.values())

    return JSONResponse(
        status_code=200 if all_healthy else 503,
        content={"status": "ready" if all_healthy else "not_ready", "checks": checks},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.WORKERS,
    )
