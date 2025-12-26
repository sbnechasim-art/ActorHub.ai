"""Training Service - Main Application."""

import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from .config import get_settings
from .routes import router

settings = get_settings()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting Training Service", version=settings.service_version)
    yield
    logger.info("Shutting down Training Service")


app = FastAPI(
    title="ActorHub Training Service",
    description="ML model training and fine-tuning service",
    version=settings.service_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.service_version,
    }


@app.get("/ready")
async def readiness_check():
    return {"status": "ready"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
