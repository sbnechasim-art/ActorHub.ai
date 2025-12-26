"""Service configuration."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service settings from environment variables."""

    # Service
    service_name: str = "identity-service"
    service_version: str = "1.0.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8001

    # Redis
    redis_url: str = "redis://localhost:6379/1"

    # ML Service
    ml_service_url: str = "http://localhost:8003"

    # Face Recognition
    similarity_threshold: float = 0.4
    min_face_quality: float = 0.5
    liveness_threshold: float = 0.7

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    # Telemetry
    otlp_endpoint: str = ""

    class Config:
        env_prefix = "IDENTITY_"
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
