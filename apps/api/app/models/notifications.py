"""
Notification, Audit, Webhook, Subscription, and Payout Models
"""

import enum
import uuid
from datetime import datetime

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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class NotificationType(str, enum.Enum):
    """Types of notifications"""
    SYSTEM = "SYSTEM"
    MARKETING = "MARKETING"
    SECURITY = "SECURITY"
    BILLING = "BILLING"
    IDENTITY = "IDENTITY"
    TRAINING = "TRAINING"
    DETECTION = "DETECTION"


class NotificationChannel(str, enum.Enum):
    """Delivery channels for notifications"""
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"


class Notification(Base):
    """User notifications"""

    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Content
    type = Column(Enum(NotificationType), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    action_url = Column(Text)
    extra_data = Column(JSONB, default=dict)

    # Delivery
    channel = Column(Enum(NotificationChannel), default=NotificationChannel.IN_APP)
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime)
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime)

    # Status
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime)

    # Relationships
    user = relationship("User", backref="notifications")

    # Constraints
    __table_args__ = (
        # Date validation
        CheckConstraint(
            "expires_at IS NULL OR expires_at > created_at",
            name="chk_notification_expires_after_created",
        ),
        CheckConstraint(
            "read_at IS NULL OR read_at >= created_at",
            name="chk_notification_read_after_created",
        ),
        CheckConstraint(
            "sent_at IS NULL OR sent_at >= created_at",
            name="chk_notification_sent_after_created",
        ),
        # Indexes
        Index("idx_notification_user_unread", "user_id", "is_read", postgresql_where="is_read = false"),
    )


class AuditAction(str, enum.Enum):
    """Types of auditable actions"""
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    EXPORT = "EXPORT"
    DOWNLOAD = "DOWNLOAD"
    VERIFY = "VERIFY"
    DETECT = "DETECT"
    TRAIN = "TRAIN"
    PURCHASE = "PURCHASE"
    REFUND = "REFUND"
    API_CALL = "API_CALL"


class AuditLog(Base):
    """Audit trail for security and compliance"""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Actor - SET NULL to preserve audit history when user/key deleted
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    api_key_id = Column(
        UUID(as_uuid=True),
        ForeignKey("api_keys.id", ondelete="SET NULL"),
    )
    ip_address = Column(String(50))
    user_agent = Column(Text)

    # Action
    action = Column(Enum(AuditAction), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)  # e.g., "identity", "actor_pack"
    resource_id = Column(UUID(as_uuid=True), index=True)

    # Details
    description = Column(Text)
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    extra_data = Column(JSONB, default=dict)

    # Request info
    request_id = Column(String(64), index=True)
    request_path = Column(Text)
    request_method = Column(String(10))

    # Status
    success = Column(Boolean, default=True)
    error_message = Column(Text)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", backref="audit_logs")
    api_key = relationship("ApiKey", backref="audit_logs")

    # Constraints
    __table_args__ = (
        # HTTP method validation
        CheckConstraint(
            "request_method IS NULL OR request_method IN ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS')",
            name="chk_audit_log_request_method",
        ),
        # Indexes for compliance queries
        Index("idx_audit_log_user_action", "user_id", "action", "created_at"),
        Index("idx_audit_log_resource", "resource_type", "resource_id", "created_at"),
    )


class WebhookEventStatus(str, enum.Enum):
    """Status of webhook event processing"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


class WebhookSource(str, enum.Enum):
    """Sources of webhook events"""
    STRIPE = "STRIPE"
    CLERK = "CLERK"
    SENDGRID = "SENDGRID"
    REPLICATE = "REPLICATE"
    ELEVENLABS = "ELEVENLABS"


class WebhookEvent(Base):
    """Track incoming webhook events for idempotency and debugging"""

    __tablename__ = "webhook_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Event identification
    event_id = Column(String(255), unique=True, nullable=False, index=True)
    source = Column(Enum(WebhookSource), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)

    # Payload
    payload = Column(JSONB, nullable=False)
    headers = Column(JSONB)

    # Processing
    status = Column(Enum(WebhookEventStatus), default=WebhookEventStatus.PENDING, index=True)
    attempts = Column(Integer, default=0)
    last_attempt_at = Column(DateTime)
    processed_at = Column(DateTime)
    error_message = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        CheckConstraint("attempts >= 0", name="chk_webhook_attempts_positive"),
        CheckConstraint(
            "processed_at IS NULL OR processed_at >= created_at",
            name="chk_webhook_processed_after_created",
        ),
        CheckConstraint(
            "last_attempt_at IS NULL OR last_attempt_at >= created_at",
            name="chk_webhook_attempt_after_created",
        ),
        # Indexes for cleanup queries
        Index("idx_webhook_status_created", "status", "created_at"),
    )


class SubscriptionStatus(str, enum.Enum):
    """Status of user subscription"""
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    CANCELED = "CANCELED"
    INCOMPLETE = "INCOMPLETE"
    TRIALING = "TRIALING"
    PAUSED = "PAUSED"


class SubscriptionPlan(str, enum.Enum):
    """Available subscription plans"""
    FREE = "FREE"
    PRO_MONTHLY = "PRO_MONTHLY"
    PRO_YEARLY = "PRO_YEARLY"
    ENTERPRISE_MONTHLY = "ENTERPRISE_MONTHLY"
    ENTERPRISE_YEARLY = "ENTERPRISE_YEARLY"


class Subscription(Base):
    """User subscriptions for billing"""

    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Stripe integration
    stripe_subscription_id = Column(String(255), unique=True, index=True)
    stripe_customer_id = Column(String(255), index=True)
    stripe_price_id = Column(String(255))

    # Plan details
    plan = Column(Enum(SubscriptionPlan), nullable=False, index=True)
    status = Column(Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.ACTIVE, index=True)

    # Pricing
    amount = Column(Float, default=0.0)
    currency = Column(String(3), default="USD")
    interval = Column(String(20))  # "month" or "year"

    # Dates
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    trial_start = Column(DateTime)
    trial_end = Column(DateTime)
    canceled_at = Column(DateTime)
    cancel_at_period_end = Column(Boolean, default=False)

    # Usage limits
    identities_limit = Column(Integer, default=3)
    api_calls_limit = Column(Integer, default=1000)
    storage_limit_mb = Column(Integer, default=100)

    # Metadata
    extra_data = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="subscriptions")

    # Constraints
    __table_args__ = (
        # Financial constraints
        CheckConstraint("amount >= 0", name="chk_subscription_amount_positive"),
        # Interval validation
        CheckConstraint(
            "interval IS NULL OR interval IN ('month', 'year')",
            name="chk_subscription_interval_valid",
        ),
        # Usage limits
        CheckConstraint("identities_limit > 0", name="chk_subscription_identities_limit_positive"),
        CheckConstraint("api_calls_limit > 0", name="chk_subscription_api_calls_limit_positive"),
        CheckConstraint("storage_limit_mb > 0", name="chk_subscription_storage_limit_positive"),
        # Period validation
        CheckConstraint(
            "current_period_end IS NULL OR current_period_start IS NULL OR current_period_end >= current_period_start",
            name="chk_subscription_period_valid",
        ),
        CheckConstraint(
            "trial_end IS NULL OR trial_start IS NULL OR trial_end >= trial_start",
            name="chk_subscription_trial_period_valid",
        ),
        # One active subscription per user
        Index(
            "idx_subscription_user_active_unique",
            "user_id",
            unique=True,
            postgresql_where="status IN ('ACTIVE', 'TRIALING', 'PAST_DUE')",
        ),
    )


class PayoutStatus(str, enum.Enum):
    """Status of creator payouts"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class PayoutMethod(str, enum.Enum):
    """Payout methods"""
    STRIPE_CONNECT = "STRIPE_CONNECT"
    PAYPAL = "PAYPAL"
    BANK_TRANSFER = "BANK_TRANSFER"


class Payout(Base):
    """Creator payouts for marketplace earnings"""

    __tablename__ = "payouts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # SET NULL to preserve financial records when user deleted
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )

    # Amount
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    fee = Column(Float, default=0.0)
    net_amount = Column(Float)

    # Payment details
    method = Column(Enum(PayoutMethod), nullable=False)
    status = Column(Enum(PayoutStatus), default=PayoutStatus.PENDING, index=True)

    # Stripe
    stripe_payout_id = Column(String(255), unique=True, index=True)
    stripe_transfer_id = Column(String(255))

    # Period
    period_start = Column(DateTime)
    period_end = Column(DateTime)

    # Transactions included
    transaction_ids = Column(JSONB, default=list)
    transaction_count = Column(Integer, default=0)

    # Processing
    requested_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    completed_at = Column(DateTime)
    failed_at = Column(DateTime)
    failure_reason = Column(Text)

    # Metadata
    extra_data = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="payouts")

    # Constraints
    __table_args__ = (
        # Financial constraints
        CheckConstraint("amount > 0", name="chk_payout_amount_positive"),
        CheckConstraint("fee >= 0", name="chk_payout_fee_positive"),
        CheckConstraint(
            "net_amount IS NULL OR net_amount >= 0",
            name="chk_payout_net_amount_positive",
        ),
        CheckConstraint(
            "net_amount IS NULL OR (net_amount <= amount AND net_amount = amount - fee)",
            name="chk_payout_net_amount_valid",
        ),
        # Transaction count
        CheckConstraint("transaction_count >= 0", name="chk_payout_transaction_count_positive"),
        # Period validation
        CheckConstraint(
            "period_end IS NULL OR period_start IS NULL OR period_end >= period_start",
            name="chk_payout_period_valid",
        ),
        # Date logic
        CheckConstraint(
            "processed_at IS NULL OR processed_at >= requested_at",
            name="chk_payout_processed_after_requested",
        ),
        CheckConstraint(
            "completed_at IS NULL OR (processed_at IS NOT NULL AND completed_at >= processed_at)",
            name="chk_payout_completed_after_processed",
        ),
        # Indexes
        Index("idx_payout_user_status", "user_id", "status"),
        Index("idx_payout_period", "period_start", "period_end"),
    )


class EarningStatus(str, enum.Enum):
    """Status of creator earnings"""
    PENDING = "PENDING"      # In holding period (7-14 days)
    AVAILABLE = "AVAILABLE"  # Ready for payout
    PAID = "PAID"           # Included in a completed payout
    REFUNDED = "REFUNDED"   # Refunded, earning reversed


class CreatorEarning(Base):
    """
    Individual earnings for creators from license sales.

    Tracks each earning separately with:
    - Holding period before becoming available
    - Link to the original license/transaction
    - Payout tracking when paid out
    """

    __tablename__ = "creator_earnings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Creator who earned this
    creator_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )

    # Source of earning
    license_id = Column(
        UUID(as_uuid=True),
        ForeignKey("licenses.id", ondelete="SET NULL"),
        index=True,
    )
    identity_id = Column(
        UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="SET NULL"),
        index=True,
    )

    # Amounts
    gross_amount = Column(Float, nullable=False)  # Total sale price
    platform_fee = Column(Float, nullable=False)  # Platform's cut (20%)
    net_amount = Column(Float, nullable=False)    # Creator's earnings (80%)
    currency = Column(String(3), default="USD")

    # Status tracking
    status = Column(Enum(EarningStatus), default=EarningStatus.PENDING, index=True)

    # Holding period
    earned_at = Column(DateTime, default=datetime.utcnow)  # When the sale happened
    available_at = Column(DateTime)  # When it becomes available (earned_at + holding_period)

    # Payout tracking
    payout_id = Column(
        UUID(as_uuid=True),
        ForeignKey("payouts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    paid_at = Column(DateTime)

    # Refund tracking
    refunded_at = Column(DateTime)
    refund_reason = Column(String(500))

    # Metadata
    description = Column(String(500))  # e.g., "License sale: Basic - Personal use"
    extra_data = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator = relationship("User", backref="earnings")
    license = relationship("License", backref="creator_earning")
    payout = relationship("Payout", backref="earnings")

    # Constraints
    __table_args__ = (
        # Financial constraints
        CheckConstraint("gross_amount > 0", name="chk_earning_gross_positive"),
        CheckConstraint("platform_fee >= 0", name="chk_earning_fee_positive"),
        CheckConstraint("net_amount > 0", name="chk_earning_net_positive"),
        CheckConstraint(
            "net_amount <= gross_amount",
            name="chk_earning_net_not_exceed_gross",
        ),
        # Date logic
        CheckConstraint(
            "available_at IS NULL OR available_at >= earned_at",
            name="chk_earning_available_after_earned",
        ),
        CheckConstraint(
            "paid_at IS NULL OR paid_at >= available_at",
            name="chk_earning_paid_after_available",
        ),
        # Indexes
        Index("idx_earning_creator_status", "creator_id", "status"),
        Index("idx_earning_available", "creator_id", "status", "available_at"),
    )
