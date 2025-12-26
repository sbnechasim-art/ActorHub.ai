"""Licensing Service - Main Application."""

import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from .config import get_settings
from .routes import router

settings = get_settings()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Licensing Service", version=settings.service_version)
    yield
    logger.info("Shutting down Licensing Service")


app = FastAPI(
    title="ActorHub Licensing Service",
    description="Content licensing and usage management",
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
app.mount("/metrics", make_asgi_app())


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.service_name, "version": settings.service_version}


@app.get("/ready")
async def readiness_check():
    return {"status": "ready"}
