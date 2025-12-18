"""
Application Configuration
Loads settings from environment variables with validation
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # App
    APP_NAME: str = "ActorHub.ai"
    APP_VERSION: str = "1.0.0"
    VERSION: str = "1.0.0"  # Alias for APP_VERSION
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production
    API_PREFIX: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8001",
        "https://actorhub.ai",
        "https://www.actorhub.ai",
        "https://api.actorhub.ai",
    ]

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/actorhub"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT Auth
    JWT_SECRET: str = "your-super-secret-jwt-key"
    JWT_REFRESH_SECRET: str = "your-super-secret-refresh-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # 15 minutes for access tokens
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 days for refresh tokens
    JWT_EXPIRE_MINUTES: int = 15  # Deprecated: Use JWT_ACCESS_TOKEN_EXPIRE_MINUTES

    # AWS/S3/MinIO
    AWS_ACCESS_KEY_ID: str = "minioadmin"
    AWS_SECRET_ACCESS_KEY: str = "minioadmin"
    AWS_REGION: str = "us-east-1"
    AWS_ENDPOINT_URL: Optional[str] = "http://localhost:9000"
    S3_ENDPOINT: Optional[str] = "http://localhost:9000"  # Alias for AWS_ENDPOINT_URL
    S3_BUCKET_ACTOR_PACKS: str = "actorhub-actor-packs"
    S3_BUCKET_UPLOADS: str = "actorhub-uploads"

    # Qdrant Vector DB
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION: str = "face_embeddings"

    # AI/ML APIs
    OPENAI_API_KEY: Optional[str] = None
    REPLICATE_API_TOKEN: Optional[str] = None
    REPLICATE_WEBHOOK_SECRET: Optional[str] = None  # For verifying webhook signatures
    ELEVENLABS_API_KEY: Optional[str] = None
    FAL_KEY: Optional[str] = None

    # Stripe Payments
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None

    # Clerk Authentication
    CLERK_WEBHOOK_SECRET: Optional[str] = None

    # Email (SendGrid)
    SENDGRID_API_KEY: Optional[str] = None
    EMAIL_FROM: str = "noreply@actorhub.ai"
    EMAIL_FROM_NAME: str = "ActorHub.ai"

    # Frontend URL (for redirects)
    FRONTEND_URL: str = "http://localhost:3000"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Monitoring
    SENTRY_DSN: Optional[str] = None

    # Feature Flags
    ENABLE_BLOCKCHAIN: bool = False
    ENABLE_ACTOR_PACKS: bool = True
    ENABLE_MARKETPLACE: bool = True
    ENABLE_VOICE_CLONING: bool = True

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds

    # Face Recognition
    FACE_SIMILARITY_THRESHOLD: float = 0.80
    FACE_DUPLICATE_THRESHOLD: float = 0.85
    FACE_EMBEDDING_SIZE: int = 512

    # Allowed Image Domains (for URL-based verification)
    ALLOWED_IMAGE_DOMAINS: List[str] = [
        "storage.actorhub.ai",
        "cdn.actorhub.ai",
        "storage.googleapis.com",
        "s3.amazonaws.com",
        "s3.us-east-1.amazonaws.com",
        "cloudfront.net",
        "imagekit.io",
        "localhost",
        "127.0.0.1",
    ]

    # Marketplace Categories
    MARKETPLACE_CATEGORIES: List[dict] = [
        {"id": "actor", "name": "Actors", "description": "Professional actors and performers"},
        {"id": "model", "name": "Models", "description": "Fashion and commercial models"},
        {"id": "influencer", "name": "Influencers", "description": "Social media personalities"},
        {"id": "character", "name": "Characters", "description": "Fictional characters and avatars"},
        {"id": "presenter", "name": "Presenters", "description": "Hosts and presenters"},
        {"id": "voice", "name": "Voice Artists", "description": "Voice-over and narration talent"},
    ]

    # Refund Policy
    REFUND_WINDOW_DAYS: int = 7
    REFUND_COOLING_HOURS: int = 1
    MAX_REFUNDS_PER_USER: int = 3

    @property
    def database_url_async(self) -> str:
        """Convert sync URL to async"""
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

    @model_validator(mode="after")
    def validate_production_settings(self):
        """Ensure critical settings are properly configured in production"""
        if not self.DEBUG:
            insecure_secrets = [
                "your-super-secret-jwt-key",
                "your-super-secret-refresh-key",
                "secret",
                "changeme",
                "",
            ]
            # Validate JWT_SECRET
            if self.JWT_SECRET in insecure_secrets or len(self.JWT_SECRET) < 32:
                raise ValueError(
                    "JWT_SECRET must be set to a secure random string (min 32 chars) in production. "
                    "Generate with: openssl rand -hex 32"
                )
            # Validate JWT_REFRESH_SECRET
            if self.JWT_REFRESH_SECRET in insecure_secrets or len(self.JWT_REFRESH_SECRET) < 32:
                raise ValueError(
                    "JWT_REFRESH_SECRET must be set to a secure random string (min 32 chars) in production. "
                    "Generate with: openssl rand -hex 32"
                )
            # Ensure secrets are different
            if self.JWT_SECRET == self.JWT_REFRESH_SECRET:
                raise ValueError(
                    "JWT_SECRET and JWT_REFRESH_SECRET must be different for security."
                )
        return self


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance"""
    return Settings()


settings = get_settings()
