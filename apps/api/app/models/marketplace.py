"""
Marketplace Models
Licenses, Transactions, and Listings
"""

import enum
import uuid
from datetime import datetime

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


class LicenseType(str, enum.Enum):
    """Types of licenses available"""

    SINGLE_USE = "SINGLE_USE"  # One-time use
    SUBSCRIPTION = "SUBSCRIPTION"  # Time-based
    UNLIMITED = "UNLIMITED"  # No limits
    CUSTOM = "CUSTOM"  # Negotiated terms


class UsageType(str, enum.Enum):
    """How the identity can be used"""

    PERSONAL = "PERSONAL"  # Non-commercial
    COMMERCIAL = "COMMERCIAL"  # Ads, products
    EDITORIAL = "EDITORIAL"  # News, documentary
    EDUCATIONAL = "EDUCATIONAL"  # Training, courses


class PaymentStatus(str, enum.Enum):
    """Payment processing status"""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    DISPUTED = "DISPUTED"


class TransactionType(str, enum.Enum):
    """Types of financial transactions"""

    PURCHASE = "PURCHASE"  # License purchase
    PAYOUT = "PAYOUT"  # Creator payout
    REFUND = "REFUND"  # Money returned
    FEE = "FEE"  # Platform fee
    SUBSCRIPTION = "SUBSCRIPTION"  # Recurring payment
    CREDIT = "CREDIT"  # Credit added to account


class ListingCategory(str, enum.Enum):
    """Categories for marketplace listings"""

    ACTOR = "ACTOR"
    MODEL = "MODEL"
    INFLUENCER = "INFLUENCER"
    CHARACTER = "CHARACTER"
    VOICE_ARTIST = "VOICE_ARTIST"
    CUSTOM = "CUSTOM"


class License(Base):
    """
    License for using a protected identity.
    Represents the legal agreement between identity owner and licensee.
    """

    __tablename__ = "licenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Parties
    identity_id = Column(
        UUID(as_uuid=True), ForeignKey("identities.id"), nullable=False, index=True
    )
    licensee_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # License terms
    license_type = Column(Enum(LicenseType), nullable=False)
    usage_type = Column(Enum(UsageType), nullable=False)

    # Scope
    project_name = Column(String(255))  # What project this is for
    project_description = Column(Text)
    allowed_platforms = Column(ARRAY(String))  # ["youtube", "tiktok", "tv"]
    allowed_regions = Column(ARRAY(String))  # ISO country codes
    excluded_uses = Column(ARRAY(String))  # Specific exclusions

    # Limits
    max_impressions = Column(Integer)
    max_duration_seconds = Column(Integer)  # For video content
    max_images = Column(Integer)
    max_outputs = Column(Integer)  # Total AI generations allowed

    # Validity
    valid_from = Column(DateTime, nullable=False, default=datetime.utcnow)
    valid_until = Column(DateTime)
    is_active = Column(Boolean, default=True)
    auto_renew = Column(Boolean, default=False)

    # Payment
    price_usd = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    stripe_payment_intent_id = Column(String(255))
    stripe_subscription_id = Column(String(255))  # For subscription licenses
    paid_at = Column(DateTime)

    # Revenue split
    platform_fee_percent = Column(Float, default=20)
    creator_payout_usd = Column(Float)
    payout_status = Column(String(50), default="pending")
    payout_at = Column(DateTime)

    # Contract
    contract_hash = Column(String(100))  # IPFS or blockchain hash
    contract_url = Column(Text)
    signed_at = Column(DateTime)
    terms_accepted = Column(Boolean, default=False)

    # Usage tracking
    current_uses = Column(Integer, default=0)
    current_impressions = Column(Integer, default=0)
    current_duration_seconds = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    identity = relationship("Identity", back_populates="licenses")
    licensee = relationship("User", foreign_keys=[licensee_id])
    transactions = relationship("Transaction", back_populates="license", lazy="dynamic")

    # Indexes
    __table_args__ = (
        Index("idx_license_dates", "valid_from", "valid_until"),
        Index("idx_license_active", "is_active", "valid_until"),
    )

    @property
    def is_valid(self) -> bool:
        """Check if license is currently valid"""
        if not self.is_active:
            return False
        if self.payment_status != PaymentStatus.COMPLETED:
            return False
        now = datetime.utcnow()
        if now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True


class Transaction(Base):
    """
    Financial transaction record.
    Tracks all money movement on the platform.
    """

    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Related entities
    license_id = Column(UUID(as_uuid=True), ForeignKey("licenses.id"), index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Transaction details
    type = Column(Enum(TransactionType), nullable=False)
    amount_usd = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    description = Column(Text)

    # Status
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)

    # Stripe
    stripe_payment_intent_id = Column(String(255))
    stripe_charge_id = Column(String(255))
    stripe_transfer_id = Column(String(255))  # For payouts

    # Extra data
    transaction_metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime)

    # Relationships
    license = relationship("License", back_populates="transactions")
    user = relationship("User")


class Listing(Base):
    """
    Marketplace listing for an Actor Pack.
    Public representation for discovery and purchase.
    """

    __tablename__ = "listings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    identity_id = Column(
        UUID(as_uuid=True), ForeignKey("identities.id"), nullable=False, index=True
    )

    # Listing info
    title = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True)
    description = Column(Text)
    short_description = Column(String(500))

    # Media
    thumbnail_url = Column(Text)
    preview_images = Column(ARRAY(Text))
    preview_video_url = Column(Text)
    demo_audio_url = Column(Text)

    # Categories & Tags
    category = Column(Enum(ListingCategory))
    tags = Column(ARRAY(String))
    style_tags = Column(ARRAY(String))  # "professional", "casual", "dramatic"

    # Pricing tiers
    pricing_tiers = Column(JSONB, default=list)
    # Example: [{"name": "Basic", "price": 99, "features": ["10 images"]},
    #           {"name": "Pro", "price": 299, "features": ["Unlimited images", "Voice"]}]

    # Availability
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    requires_approval = Column(Boolean, default=False)

    # Stats
    view_count = Column(Integer, default=0)
    favorite_count = Column(Integer, default=0)
    license_count = Column(Integer, default=0)
    avg_rating = Column(Float)
    rating_count = Column(Integer, default=0)

    # SEO
    meta_title = Column(String(255))
    meta_description = Column(Text)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime)

    # Relationships
    identity = relationship("Identity", back_populates="listings")

    # Indexes
    __table_args__ = (
        Index("idx_listing_category_active", "category", "is_active"),
        Index("idx_listing_featured", "is_featured", "is_active"),
    )
