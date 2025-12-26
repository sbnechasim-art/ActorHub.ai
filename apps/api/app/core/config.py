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

    # CORS - Development ports (3000-3010) and production domains
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:3004",
        "http://localhost:3005",
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

    # Cookie Settings (httpOnly for security)
    COOKIE_DOMAIN: Optional[str] = None  # None = current domain only
    COOKIE_SECURE: bool = True  # Only send over HTTPS (set False for local dev)
    COOKIE_SAMESITE: str = "lax"  # "strict", "lax", or "none"
    COOKIE_ACCESS_TOKEN_NAME: str = "access_token"
    COOKIE_REFRESH_TOKEN_NAME: str = "refresh_token"

    # AWS/S3/MinIO
    AWS_ACCESS_KEY_ID: str = "minioadmin"
    AWS_SECRET_ACCESS_KEY: str = "minioadmin"
    AWS_REGION: str = "us-east-1"
    AWS_ENDPOINT_URL: Optional[str] = "http://localhost:9000"
    S3_ENDPOINT: Optional[str] = "http://localhost:9000"  # Alias for AWS_ENDPOINT_URL
    S3_BUCKET_ACTOR_PACKS: str = "actorhub-actor-packs"
    S3_BUCKET_UPLOADS: str = "actorhub-uploads"
    S3_PUBLIC_URL: Optional[str] = None  # Public URL for external access (ngrok/CDN)

    # Qdrant Vector DB
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION: str = "face_embeddings"

    # AI/ML APIs
    OPENAI_API_KEY: Optional[str] = None
    REPLICATE_API_TOKEN: Optional[str] = None
    REPLICATE_WEBHOOK_SECRET: Optional[str] = None  # For verifying webhook signatures
    REPLICATE_USERNAME: str = "sbnechasim-art"  # Replicate account username for model destinations
    # HIGH FIX: Moved from hardcoded value in training.py to config
    # ostris/flux-dev-lora-trainer version - update when new versions are available
    REPLICATE_LORA_TRAINER_VERSION: str = "26dce37af90b9d997eeb970d92e47de3064d46c300504ae376c75bef6a9022d2"
    REPLICATE_XTTS_VERSION: str = "684bc3855b37866c0c65add2ff39c78f3dea3f4ff103a436465326e0f438d55e"
    ELEVENLABS_API_KEY: Optional[str] = None
    FAL_KEY: Optional[str] = None

    # Stripe Payments
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None

    # Clerk Authentication
    CLERK_WEBHOOK_SECRET: Optional[str] = None

    # OAuth Providers
    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    # GitHub OAuth
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    # OAuth state encryption key (generate with: openssl rand -hex 32)
    OAUTH_STATE_SECRET: str = "your-oauth-state-secret-key"

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

    # Distributed Tracing (OpenTelemetry)
    ENABLE_TRACING: bool = True
    OTEL_EXPORTER_TYPE: str = "console"  # console, jaeger, otlp, zipkin
    JAEGER_HOST: str = "localhost"
    JAEGER_PORT: int = 6831
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    ZIPKIN_ENDPOINT: str = "http://localhost:9411/api/v2/spans"

    # Feature Flags
    ENABLE_BLOCKCHAIN: bool = False
    ENABLE_ACTOR_PACKS: bool = True
    ENABLE_MARKETPLACE: bool = True
    ENABLE_VOICE_CLONING: bool = True

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds

    # Creator Payouts
    PAYOUT_HOLDING_DAYS: int = 7  # Days before earnings become available
    PAYOUT_MINIMUM_USD: float = 50.0  # Minimum balance for payout
    PAYOUT_PLATFORM_FEE_PERCENT: float = 20.0  # Platform takes 20%
    PAYOUT_AUTO_ENABLED: bool = True  # Enable automatic weekly payouts

    # Face Recognition
    FACE_SIMILARITY_THRESHOLD: float = 0.70  # Lowered from 0.80 for better UX
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
    MAX_REFUND_AMOUNT_USD: float = 10000.0  # $10,000 max refund

    # Upload Size Limits (in bytes)
    MAX_BODY_SIZE_BYTES: int = 10 * 1024 * 1024  # 10MB for regular requests
    MAX_FILE_UPLOAD_SIZE_BYTES: int = 500 * 1024 * 1024  # 500MB for training
    MAX_IMAGE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10MB per image
    MAX_AUDIO_SIZE_BYTES: int = 50 * 1024 * 1024  # 50MB per audio file
    MAX_TRAINING_IMAGES: int = 100  # Maximum images for training

    # Timeouts (in seconds)
    GENERATION_TIMEOUT: int = 300  # 5 minutes for AI generation
    S3_CONNECT_TIMEOUT: int = 10
    S3_READ_TIMEOUT: int = 60
    WEBHOOK_TIMEOUT: int = 10
    REPLICATE_POLL_INITIAL_DELAY: int = 10
    REPLICATE_POLL_MAX_DELAY: int = 60

    # Security
    HSTS_MAX_AGE_SECONDS: int = 31536000  # 1 year
    CORS_PREFLIGHT_MAX_AGE: int = 3600  # 1 hour

    # Pagination
    MAX_PAGE_NUMBER: int = 500
    MAX_OFFSET: int = 10000
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

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
