"""
Notification, Audit, Webhook, Subscription, and Payout Models
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
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
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

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

    # Actor
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"))
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
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

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
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

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
