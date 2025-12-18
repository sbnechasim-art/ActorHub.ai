"""
CORS Configuration
Production-ready CORS setup
"""

from typing import List

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.core.config import settings


def setup_cors(app: FastAPI) -> None:
    """
    Configure CORS for the application.

    In production:
    - Only allow specific origins
    - Limit exposed headers
    - Set appropriate max age for preflight caching
    """

    # Define allowed origins based on environment
    if settings.ENVIRONMENT == "development":
        # Allow all in development
        origins = ["*"]
    else:
        # Production origins
        origins = [
            "https://actorhub.ai",
            "https://www.actorhub.ai",
            "https://app.actorhub.ai",
            "https://studio.actorhub.ai",
            "https://admin.actorhub.ai",
        ]

        # Add custom origins from settings
        if hasattr(settings, "CORS_ORIGINS") and settings.CORS_ORIGINS:
            origins.extend(settings.CORS_ORIGINS.split(","))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-API-Key",
            "X-Request-ID",
            "X-Client-Version",
            "Accept",
            "Accept-Language",
            "Origin",
        ],
        expose_headers=[
            "X-Request-ID",
            "X-Response-Time",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
        max_age=600,  # Cache preflight for 10 minutes
    )


def get_cors_origins() -> List[str]:
    """Get list of allowed CORS origins"""
    if settings.ENVIRONMENT == "development":
        return ["*"]

    origins = [
        "https://actorhub.ai",
        "https://www.actorhub.ai",
        "https://app.actorhub.ai",
    ]

    if hasattr(settings, "CORS_ORIGINS") and settings.CORS_ORIGINS:
        origins.extend(settings.CORS_ORIGINS.split(","))

    return origins
