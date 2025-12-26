"""Identity Service - Main Application."""

import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from .config import get_settings
from .routes import router
from .middleware import RateLimitMiddleware

settings = get_settings()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting Identity Service", version=settings.service_version)
    yield
    logger.info("Shutting down Identity Service")


app = FastAPI(
    title="ActorHub Identity Service",
    description="Identity verification and face recognition service",
    version=settings.service_version,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
app.add_middleware(RateLimitMiddleware)

# Routes
app.include_router(router, prefix="/api/v1")

# Metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.service_version,
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    # Check dependencies
    return {"status": "ready"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
