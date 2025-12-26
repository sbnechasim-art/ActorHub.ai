"""Delivery service configuration."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service settings."""

    service_name: str = "delivery-service"
    service_version: str = "1.0.0"
    debug: bool = False

    host: str = "0.0.0.0"
    port: int = 8004

    # Redis for caching
    redis_url: str = "redis://localhost:6379/5"

    # AWS S3
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    s3_bucket_content: str = "actorhub-content"
    s3_bucket_generated: str = "actorhub-generated"

    # CloudFront
    cloudfront_domain: str = ""
    cloudfront_key_pair_id: str = ""
    cloudfront_private_key: str = ""

    # Signed URL settings
    signed_url_expiry_seconds: int = 3600  # 1 hour
    thumbnail_sizes: list[int] = [128, 256, 512]

    # Rate limiting
    max_downloads_per_minute: int = 60

    class Config:
        env_prefix = "DELIVERY_"
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
