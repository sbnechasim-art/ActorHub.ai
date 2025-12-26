"""Licensing service configuration."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service settings."""

    service_name: str = "licensing-service"
    service_version: str = "1.0.0"
    debug: bool = False

    host: str = "0.0.0.0"
    port: int = 8003

    # Database
    database_url: str = "postgresql+asyncpg://localhost/actorhub"

    # Redis
    redis_url: str = "redis://localhost:6379/4"

    # JWT for license tokens
    license_secret_key: str = "change-me-in-production"
    license_algorithm: str = "HS256"
    license_expiry_days: int = 365

    # License limits
    free_generation_limit: int = 10
    creator_generation_limit: int = 100
    pro_generation_limit: int = 1000

    class Config:
        env_prefix = "LICENSING_"
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
