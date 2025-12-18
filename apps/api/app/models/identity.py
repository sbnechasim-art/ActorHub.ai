"""
Identity and Actor Pack Models
Core entities of the platform
"""

import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class ProtectionLevel(str, enum.Enum):
    """Protection tier levels"""

    FREE = "FREE"  # Basic protection
    PRO = "PRO"  # Enhanced + alerts
    ENTERPRISE = "ENTERPRISE"  # Full legal support


class IdentityStatus(str, enum.Enum):
    """Identity verification status"""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class TrainingStatus(str, enum.Enum):
    """Actor Pack training status"""

    PENDING = "PENDING"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Identity(Base):
    """
    Core identity record - the foundation of the platform.
    Represents a protected digital identity with face embeddings.
    """

    __tablename__ = "identities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Owner info
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Identity data
    display_name = Column(String(255), nullable=False)
    legal_name = Column(String(255))  # Encrypted in production
    bio = Column(Text)
    profile_image_url = Column(Text)

    # Face embeddings (512-dimensional vector from ArcFace)
    face_embedding = Column(Vector(512))
    face_embedding_backup = Column(Vector(512))  # From different angle

    # Status & verification
    status = Column(Enum(IdentityStatus), default=IdentityStatus.PENDING, index=True)
    verified_at = Column(DateTime)
    verification_method = Column(String(50))  # "selfie", "id_document", "video"
    verification_data = Column(JSONB)  # Additional verification info

    # Protection settings
    protection_level = Column(Enum(ProtectionLevel), default=ProtectionLevel.FREE)
    allow_commercial_use = Column(Boolean, default=False)
    allow_ai_training = Column(Boolean, default=False)
    allow_deepfake = Column(Boolean, default=False)

    # Restrictions
    blocked_categories = Column(ARRAY(String), default=list)  # ["adult", "political", "gambling"]
    blocked_brands = Column(ARRAY(String), default=list)
    blocked_regions = Column(ARRAY(String), default=list)  # ISO country codes
    custom_restrictions = Column(JSONB, default=dict)

    # Pricing (if allowing commercial use)
    base_license_fee = Column(Float, default=0)  # USD
    hourly_rate = Column(Float, default=0)  # For video content
    per_image_rate = Column(Float, default=0)
    revenue_share_percent = Column(Float, default=70)  # Creator gets this %

    # Blockchain (optional)
    nft_token_id = Column(String(100))
    nft_contract_address = Column(String(100))
    nft_minted_at = Column(DateTime)
    blockchain_hash = Column(String(100))  # Proof of registration

    # Stats
    total_verifications = Column(Integer, default=0)
    total_licenses = Column(Integer, default=0)
    total_revenue = Column(Float, default=0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime)  # Soft delete

    # Relationships
    user = relationship("User", back_populates="identities")
    actor_pack = relationship("ActorPack", back_populates="identity", uselist=False)
    licenses = relationship("License", back_populates="identity", lazy="dynamic")
    usage_logs = relationship("UsageLog", back_populates="identity", lazy="dynamic")
    listings = relationship("Listing", back_populates="identity", lazy="dynamic")

    # Indexes
    __table_args__ = (
        Index("idx_identity_user_status", "user_id", "status"),
        Index("idx_identity_commercial", "allow_commercial_use", "status"),
    )


class ActorPack(Base):
    """
    Trained model package for an identity.
    Contains face, voice, and motion models.
    """

    __tablename__ = "actor_packs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    identity_id = Column(UUID(as_uuid=True), ForeignKey("identities.id"), unique=True, index=True)

    # Pack info
    name = Column(String(255), nullable=False)
    description = Column(Text)
    version = Column(String(20), default="1.0.0")
    slug = Column(String(100), unique=True)  # For URL

    # Training status
    training_status = Column(Enum(TrainingStatus), default=TrainingStatus.PENDING)
    training_started_at = Column(DateTime)
    training_completed_at = Column(DateTime)
    training_error = Column(Text)
    training_progress = Column(Integer, default=0)  # 0-100

    # Training inputs
    training_images_count = Column(Integer, default=0)
    training_audio_seconds = Column(Float, default=0)
    training_video_seconds = Column(Float, default=0)

    # Quality metrics (0-100)
    # TODO: Implement automated quality assessment pipeline
    # - Use BRISQUE/NIQE for image quality scoring
    # - Compare generated vs original for authenticity
    # - Run consistency checks across multiple generations
    quality_score = Column(Float)
    authenticity_score = Column(Float)  # How real does generated content look
    consistency_score = Column(Float)  # Consistency across outputs
    voice_quality_score = Column(Float)  # Voice clone quality

    # Storage
    s3_bucket = Column(String(255))
    s3_key = Column(String(500))
    file_size_bytes = Column(Float)
    checksum = Column(String(64))  # SHA256

    # Components included
    components = Column(JSONB, default=dict)
    # Example: {"face": {"model": "arcface", "version": "1.0"},
    #           "voice": {"provider": "elevenlabs", "voice_id": "xxx"}}

    # Model references
    # TODO: Implement LoRA training pipeline
    # - Integrate with Replicate API or local training
    # - Support SDXL LoRA fine-tuning with ~20 images
    # - Store model weights in S3 with versioning
    lora_model_url = Column(Text)
    voice_model_id = Column(String(255))
    # TODO: Implement motion capture extraction
    # - Extract facial landmarks from video using MediaPipe
    # - Generate ARKit-compatible blendshapes
    # - Store motion data in efficient binary format
    motion_data_url = Column(Text)

    # Pricing
    base_price_usd = Column(Float, default=0)
    price_per_second_usd = Column(Float, default=0)
    price_per_image_usd = Column(Float, default=0)

    # Stats
    total_downloads = Column(Integer, default=0)
    total_uses = Column(Integer, default=0)
    total_revenue_usd = Column(Float, default=0)
    avg_rating = Column(Float)
    rating_count = Column(Integer, default=0)

    # Availability
    is_public = Column(Boolean, default=False)
    is_available = Column(Boolean, default=True)
    requires_approval = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    identity = relationship("Identity", back_populates="actor_pack")


class UsageLog(Base):
    """
    Log of every verification check or identity usage.
    Critical for tracking, billing, and analytics.
    """

    __tablename__ = "usage_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # What was checked/used
    identity_id = Column(UUID(as_uuid=True), ForeignKey("identities.id"), index=True)
    license_id = Column(UUID(as_uuid=True), ForeignKey("licenses.id"), index=True)
    actor_pack_id = Column(UUID(as_uuid=True), ForeignKey("actor_packs.id"))

    # Who
    requester_id = Column(UUID(as_uuid=True), index=True)  # User or API key owner
    requester_type = Column(String(50))  # "platform", "user", "api"
    requester_name = Column(String(255))
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"))

    # What
    action = Column(String(50), nullable=False, index=True)  # "verify", "generate", "download"
    endpoint = Column(String(255))

    # Request details
    request_metadata = Column(JSONB)
    # Example: {"platform": "sora", "content_type": "video", "duration_seconds": 30}

    # Match details (for verify actions)
    similarity_score = Column(Float)
    faces_detected = Column(Integer)
    matched = Column(Boolean)

    # Result
    result = Column(String(50))  # "allowed", "blocked", "not_found", "error"
    result_reason = Column(Text)
    response_time_ms = Column(Integer)

    # Billing
    credits_used = Column(Float, default=0)
    amount_charged_usd = Column(Float, default=0)
    billed = Column(Boolean, default=False)

    # Client info
    ip_address = Column(String(50))
    user_agent = Column(Text)
    country_code = Column(String(2))

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    identity = relationship("Identity", back_populates="usage_logs")
    actor_pack = relationship("ActorPack", backref="usage_logs")
    api_key = relationship("ApiKey", backref="usage_logs")
    license = relationship("License", backref="usage_logs")

    # Indexes for analytics
    __table_args__ = (
        Index("idx_usage_identity_date", "identity_id", "created_at"),
        Index("idx_usage_action_date", "action", "created_at"),
        Index("idx_usage_requester", "requester_id", "created_at"),
    )
