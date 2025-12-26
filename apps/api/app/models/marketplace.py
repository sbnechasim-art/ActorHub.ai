"""
Marketplace Models
Licenses, Transactions, and Listings
"""

import enum
import uuid
from datetime import datetime, timezone

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

# Valid status values
LICENSE_TYPE_VALUES = ('SINGLE_USE', 'SUBSCRIPTION', 'UNLIMITED', 'CUSTOM')
USAGE_TYPE_VALUES = ('PERSONAL', 'COMMERCIAL', 'EDITORIAL', 'EDUCATIONAL')
PAYMENT_STATUS_VALUES = ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'REFUNDED', 'DISPUTED')
TRANSACTION_TYPE_VALUES = ('PURCHASE', 'PAYOUT', 'REFUND', 'FEE', 'SUBSCRIPTION', 'CREDIT')
LISTING_CATEGORY_VALUES = ('ACTOR', 'MODEL', 'INFLUENCER', 'CHARACTER', 'PRESENTER', 'VOICE', 'VOICE_ARTIST', 'CUSTOM')


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
    PRESENTER = "PRESENTER"
    VOICE = "VOICE"
    VOICE_ARTIST = "VOICE_ARTIST"
    CUSTOM = "CUSTOM"


class License(Base):
    """
    License for using a protected identity.
    Represents the legal agreement between identity owner and licensee.
    """

    __tablename__ = "licenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Parties - SET NULL on delete to preserve license history
    identity_id = Column(
        UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="SET NULL"),
        index=True,
    )
    licensee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )

    # License terms (String to match VARCHAR in DB)
    license_type = Column(String(20), nullable=False)
    usage_type = Column(String(20), nullable=False)

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
    payment_status = Column(String(20), default="PENDING")
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

    # Indexes and constraints
    __table_args__ = (
        # Status value constraints
        CheckConstraint(
            "license_type IN ('SINGLE_USE', 'SUBSCRIPTION', 'UNLIMITED', 'CUSTOM')",
            name="chk_license_type",
        ),
        CheckConstraint(
            "usage_type IN ('PERSONAL', 'COMMERCIAL', 'EDITORIAL', 'EDUCATIONAL')",
            name="chk_license_usage_type",
        ),
        CheckConstraint(
            "payment_status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'REFUNDED', 'DISPUTED')",
            name="chk_license_payment_status",
        ),
        # Financial constraints
        CheckConstraint("price_usd >= 0", name="chk_license_price_positive"),
        CheckConstraint(
            "creator_payout_usd IS NULL OR (creator_payout_usd >= 0 AND creator_payout_usd <= price_usd)",
            name="chk_license_payout_valid",
        ),
        CheckConstraint(
            "platform_fee_percent >= 0 AND platform_fee_percent <= 100",
            name="chk_license_fee_percent_range",
        ),
        # Usage constraints
        CheckConstraint("current_uses >= 0", name="chk_license_uses_positive"),
        CheckConstraint("current_impressions >= 0", name="chk_license_impressions_positive"),
        CheckConstraint("current_duration_seconds >= 0", name="chk_license_duration_positive"),
        # Date validation
        CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name="chk_license_dates_valid",
        ),
        # Limit constraints
        CheckConstraint("max_impressions IS NULL OR max_impressions > 0", name="chk_license_max_impressions"),
        CheckConstraint("max_outputs IS NULL OR max_outputs > 0", name="chk_license_max_outputs"),
        # Indexes
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
        now = datetime.now(timezone.utc)
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

    # Related entities - SET NULL on delete to preserve financial records
    license_id = Column(
        UUID(as_uuid=True),
        ForeignKey("licenses.id", ondelete="SET NULL"),
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )

    # Transaction details (String to match VARCHAR in DB)
    type = Column(String(20), nullable=False)
    amount_usd = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    description = Column(Text)

    # Status
    status = Column(String(20), default="PENDING")

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

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "type IN ('PURCHASE', 'PAYOUT', 'REFUND', 'FEE', 'SUBSCRIPTION', 'CREDIT')",
            name="chk_transaction_type",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'REFUNDED', 'DISPUTED')",
            name="chk_transaction_status",
        ),
        CheckConstraint("amount_usd != 0", name="chk_transaction_amount_nonzero"),
    )


class Listing(Base):
    """
    Marketplace listing for an Actor Pack.
    Public representation for discovery and purchase.
    """

    __tablename__ = "listings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    identity_id = Column(
        UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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

    # Categories & Tags (String to match VARCHAR in DB)
    category = Column(String(20))
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

    # Indexes and constraints
    __table_args__ = (
        # Category constraint
        CheckConstraint(
            "category IS NULL OR category IN ('ACTOR', 'MODEL', 'INFLUENCER', 'CHARACTER', 'PRESENTER', 'VOICE', 'VOICE_ARTIST', 'CUSTOM')",
            name="chk_listing_category",
        ),
        # Stats constraints
        CheckConstraint("view_count >= 0", name="chk_listing_view_count_positive"),
        CheckConstraint("favorite_count >= 0", name="chk_listing_favorite_count_positive"),
        CheckConstraint("license_count >= 0", name="chk_listing_license_count_positive"),
        CheckConstraint("rating_count >= 0", name="chk_listing_rating_count_positive"),
        CheckConstraint(
            "avg_rating IS NULL OR (avg_rating >= 0 AND avg_rating <= 5)",
            name="chk_listing_avg_rating_range",
        ),
        # One active listing per identity
        Index(
            "idx_listing_identity_unique_active",
            "identity_id",
            unique=True,
            postgresql_where="is_active = true",
        ),
        # Indexes
        Index("idx_listing_category_active", "category", "is_active"),
        Index("idx_listing_featured", "is_featured", "is_active"),
    )
