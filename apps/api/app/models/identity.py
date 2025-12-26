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
    CheckConstraint,
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

# Valid status values for constraints
IDENTITY_STATUS_VALUES = ('PENDING', 'PROCESSING', 'VERIFIED', 'REJECTED', 'SUSPENDED')
TRAINING_STATUS_VALUES = ('PENDING', 'QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED')
PROTECTION_LEVEL_VALUES = ('FREE', 'PRO', 'ENTERPRISE')


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

    # Owner info - CASCADE on user delete
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identity data
    display_name = Column(String(255), nullable=False)
    legal_name = Column(String(255))  # Encrypted in production
    bio = Column(Text)
    profile_image_url = Column(Text)

    # Face embeddings (512-dimensional vector from ArcFace)
    face_embedding = Column(Vector(512))
    face_embedding_backup = Column(Vector(512))  # From different angle

    # Status & verification (String to match VARCHAR in DB)
    status = Column(String(20), default="PENDING", index=True)
    verified_at = Column(DateTime)
    verification_method = Column(String(50))  # "selfie", "id_document", "video"
    verification_data = Column(JSONB)  # Additional verification info

    # Protection settings (String to match VARCHAR in DB)
    protection_level = Column(String(20), default="FREE")
    allow_commercial_use = Column(Boolean, default=False)
    allow_ai_training = Column(Boolean, default=False)
    allow_deepfake = Column(Boolean, default=False)
    show_in_public_gallery = Column(Boolean, default=False)

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

    # Relationships with proper cascade behavior
    user = relationship("User", back_populates="identities")
    actor_pack = relationship(
        "ActorPack",
        back_populates="identity",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    licenses = relationship("License", back_populates="identity", lazy="dynamic")
    usage_logs = relationship("UsageLog", back_populates="identity", lazy="dynamic")
    listings = relationship(
        "Listing",
        back_populates="identity",
        lazy="dynamic",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Indexes and constraints
    __table_args__ = (
        # Status value constraints
        CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'VERIFIED', 'REJECTED', 'SUSPENDED')",
            name="chk_identity_status",
        ),
        CheckConstraint(
            "protection_level IN ('FREE', 'PRO', 'ENTERPRISE')",
            name="chk_identity_protection_level",
        ),
        # Pricing constraints
        CheckConstraint("base_license_fee >= 0", name="chk_identity_base_fee_positive"),
        CheckConstraint("hourly_rate >= 0", name="chk_identity_hourly_rate_positive"),
        CheckConstraint("per_image_rate >= 0", name="chk_identity_per_image_rate_positive"),
        CheckConstraint(
            "revenue_share_percent >= 0 AND revenue_share_percent <= 100",
            name="chk_identity_revenue_share_range",
        ),
        # Stats constraints
        CheckConstraint("total_verifications >= 0", name="chk_identity_total_verifications_positive"),
        CheckConstraint("total_licenses >= 0", name="chk_identity_total_licenses_positive"),
        CheckConstraint("total_revenue >= 0", name="chk_identity_total_revenue_positive"),
        # Indexes
        Index("idx_identity_user_status", "user_id", "status"),
        Index("idx_identity_commercial", "allow_commercial_use", "status"),
        Index(
            "idx_identity_user_display_name_unique",
            "user_id",
            "display_name",
            unique=True,
            postgresql_where="deleted_at IS NULL",
        ),
        Index("idx_identity_not_deleted", "id", postgresql_where="deleted_at IS NULL"),
    )


class ActorPack(Base):
    """
    Trained model package for an identity.
    Contains face, voice, and motion models.
    """

    __tablename__ = "actor_packs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    identity_id = Column(
        UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Pack info
    name = Column(String(255), nullable=False)
    description = Column(Text)
    version = Column(String(20), default="1.0.0")
    slug = Column(String(100), unique=True)  # For URL

    # Training status (String to match VARCHAR in DB)
    training_status = Column(String(20), default="PENDING")
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

    # Constraints and Indexes
    __table_args__ = (
        # Status constraint
        CheckConstraint(
            "training_status IN ('PENDING', 'QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED')",
            name="chk_actor_pack_training_status",
        ),
        # Progress range
        CheckConstraint(
            "training_progress >= 0 AND training_progress <= 100",
            name="chk_actor_pack_progress_range",
        ),
        # Quality score ranges
        CheckConstraint(
            "quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 100)",
            name="chk_actor_pack_quality_range",
        ),
        CheckConstraint(
            "authenticity_score IS NULL OR (authenticity_score >= 0 AND authenticity_score <= 100)",
            name="chk_actor_pack_authenticity_range",
        ),
        CheckConstraint(
            "consistency_score IS NULL OR (consistency_score >= 0 AND consistency_score <= 100)",
            name="chk_actor_pack_consistency_range",
        ),
        CheckConstraint(
            "voice_quality_score IS NULL OR (voice_quality_score >= 0 AND voice_quality_score <= 100)",
            name="chk_actor_pack_voice_quality_range",
        ),
        # Pricing constraints
        CheckConstraint("base_price_usd >= 0", name="chk_actor_pack_base_price_positive"),
        CheckConstraint("price_per_second_usd >= 0", name="chk_actor_pack_price_per_second_positive"),
        CheckConstraint("price_per_image_usd >= 0", name="chk_actor_pack_price_per_image_positive"),
        # Stats constraints
        CheckConstraint("total_downloads >= 0", name="chk_actor_pack_downloads_positive"),
        CheckConstraint("total_uses >= 0", name="chk_actor_pack_uses_positive"),
        CheckConstraint("total_revenue_usd >= 0", name="chk_actor_pack_revenue_positive"),
        CheckConstraint("rating_count >= 0", name="chk_actor_pack_rating_count_positive"),
        CheckConstraint(
            "file_size_bytes IS NULL OR file_size_bytes >= 0",
            name="chk_actor_pack_file_size_positive",
        ),
        # Indexes for common queries
        Index("idx_actor_pack_status", "training_status"),
        Index("idx_actor_pack_available_public", "is_available", "is_public"),
        Index(
            "idx_actor_pack_completed_available",
            "identity_id",
            postgresql_where="training_status = 'COMPLETED' AND is_available = true",
        ),
    )


class UsageLog(Base):
    """
    Log of every verification check or identity usage.
    Critical for tracking, billing, and analytics.
    """

    __tablename__ = "usage_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # What was checked/used - SET NULL on delete to preserve history
    identity_id = Column(
        UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="SET NULL"),
        index=True,
    )
    license_id = Column(
        UUID(as_uuid=True),
        ForeignKey("licenses.id", ondelete="SET NULL"),
        index=True,
    )
    actor_pack_id = Column(
        UUID(as_uuid=True),
        ForeignKey("actor_packs.id", ondelete="SET NULL"),
    )

    # Who
    requester_id = Column(UUID(as_uuid=True), index=True)  # User or API key owner
    requester_type = Column(String(50))  # "platform", "user", "api"
    requester_name = Column(String(255))
    api_key_id = Column(
        UUID(as_uuid=True),
        ForeignKey("api_keys.id", ondelete="SET NULL"),
    )

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

    # Indexes and constraints
    __table_args__ = (
        # Validation constraints
        CheckConstraint(
            "response_time_ms IS NULL OR response_time_ms >= 0",
            name="chk_usage_log_response_time_positive",
        ),
        CheckConstraint(
            "similarity_score IS NULL OR (similarity_score >= 0 AND similarity_score <= 1)",
            name="chk_usage_log_similarity_range",
        ),
        CheckConstraint("credits_used >= 0", name="chk_usage_log_credits_positive"),
        CheckConstraint("amount_charged_usd >= 0", name="chk_usage_log_amount_positive"),
        CheckConstraint("faces_detected IS NULL OR faces_detected >= 0", name="chk_usage_log_faces_positive"),
        # Indexes for analytics
        Index("idx_usage_identity_date", "identity_id", "created_at"),
        Index("idx_usage_action_date", "action", "created_at"),
        Index("idx_usage_requester", "requester_id", "created_at"),
    )
