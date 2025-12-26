"""Training service configuration."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service settings."""

    # Service
    service_name: str = "training-service"
    service_version: str = "1.0.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8002

    # Redis/Celery
    redis_url: str = "redis://localhost:6379/2"
    celery_broker_url: str = "redis://localhost:6379/3"
    celery_result_backend: str = "redis://localhost:6379/3"

    # AWS S3
    aws_region: str = "us-east-1"
    s3_bucket_training: str = "actorhub-training"
    s3_bucket_models: str = "actorhub-models"

    # Replicate API
    replicate_api_token: str = ""
    replicate_model_version: str = "stability-ai/sdxl"

    # Training
    max_images_per_pack: int = 20
    min_images_per_pack: int = 5
    training_timeout: int = 3600  # 1 hour

    # Webhooks
    webhook_callback_url: str = ""

    class Config:
        env_prefix = "TRAINING_"
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
