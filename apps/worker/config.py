"""
Worker Configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class WorkerSettings(BaseSettings):
    # Redis
    REDIS_URL: str = "redis://localhost:6380/0"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/actorhub"

    # S3/MinIO
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_ACTOR_PACKS: str = "actor-packs"
    S3_BUCKET_UPLOADS: str = "uploads"

    # Qdrant
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "face_embeddings"

    # Face Recognition
    FACE_EMBEDDING_SIZE: int = 512
    FACE_SIMILARITY_THRESHOLD: float = 0.85

    # Mock Modes (for local dev)
    FACE_RECOGNITION_MOCK: bool = True
    QUALITY_ASSESSMENT_MOCK: bool = True

    # External APIs
    ELEVENLABS_API_KEY: str = ""
    REPLICATE_API_TOKEN: str = ""

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6380/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6380/1"

    # Stripe
    STRIPE_SECRET_KEY: str = ""

    # SendGrid Email
    SENDGRID_API_KEY: str = ""
    EMAIL_FROM: str = "noreply@actorhub.ai"
    EMAIL_FROM_NAME: str = "ActorHub.ai"
    APP_NAME: str = "ActorHub.ai"
    FRONTEND_URL: str = "http://localhost:3000"

    # Payouts
    PAYOUT_HOLDING_DAYS: int = 7
    PAYOUT_MINIMUM_USD: float = 50.0
    PAYOUT_PLATFORM_FEE_PERCENT: float = 20.0
    PAYOUT_AUTO_ENABLED: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> WorkerSettings:
    return WorkerSettings()


settings = get_settings()
