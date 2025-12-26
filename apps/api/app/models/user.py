"""
User and API Key Models
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    USER = "USER"
    CREATOR = "CREATOR"
    ADMIN = "ADMIN"


class UserTier(str, enum.Enum):
    FREE = "FREE"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


class User(Base):
    """User account"""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Basic info
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255))  # Null if using OAuth
    first_name = Column(String(100))
    last_name = Column(String(100))
    display_name = Column(String(100))
    avatar_url = Column(Text)

    # Auth
    clerk_user_id = Column(String(255), unique=True, index=True)  # If using Clerk
    email_verified = Column(Boolean, default=False)
    phone_number = Column(String(20))
    phone_verified = Column(Boolean, default=False)

    # OAuth (Google, GitHub, etc.)
    oauth_provider = Column(String(50))  # Primary OAuth provider: google, github
    oauth_provider_id = Column(String(255))  # ID from OAuth provider
    oauth_accounts = Column(JSONB, default=dict)  # {"google": {...}, "github": {...}}

    # Role & Tier (String to match VARCHAR in DB)
    role = Column(String(20), default="USER")
    tier = Column(String(20), default="FREE")

    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)  # Identity verified
    verified_at = Column(DateTime)

    # 2FA / Authentication
    totp_secret = Column(String(32))
    backup_codes = Column(JSONB)
    is_2fa_enabled = Column(Boolean, default=False)
    password_reset_token = Column(String(64))
    password_reset_expires = Column(DateTime)
    email_verification_token = Column(String(64))
    email_verification_expires = Column(DateTime)
    # SECURITY: Track password changes to invalidate existing sessions
    password_changed_at = Column(DateTime)

    # GDPR Consent
    consent_marketing = Column(Boolean, default=False)
    consent_analytics = Column(Boolean, default=True)
    consent_third_party = Column(Boolean, default=False)
    consent_ai_training = Column(Boolean, default=False)
    consent_updated_at = Column(DateTime)
    terms_accepted_at = Column(DateTime)
    privacy_accepted_at = Column(DateTime)
    cookie_consent = Column(JSONB)
    cookie_consent_at = Column(DateTime)
    age_verified = Column(Boolean, default=False)
    age_verified_at = Column(DateTime)
    last_export_request = Column(DateTime)
    deletion_requested_at = Column(DateTime)
    deletion_scheduled_for = Column(DateTime)

    # Billing
    stripe_customer_id = Column(String(255))
    stripe_connect_account_id = Column(String(255))  # For receiving payouts
    billing_email = Column(String(255))

    # Preferences
    preferences = Column(JSONB, default=dict)
    notification_settings = Column(JSONB, default=dict)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)
    deleted_at = Column(DateTime)  # Soft delete support

    # Relationships with proper cascade behavior
    identities = relationship(
        "Identity",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    api_keys = relationship(
        "ApiKey",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    purchases = relationship("License", foreign_keys="License.licensee_id", lazy="dynamic")

    # Table constraints and indexes
    __table_args__ = (
        CheckConstraint("role IN ('USER', 'CREATOR', 'ADMIN')", name="chk_user_role"),
        CheckConstraint("tier IN ('FREE', 'PRO', 'ENTERPRISE')", name="chk_user_tier"),
        CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name="chk_user_email_format"
        ),
        Index("idx_user_not_deleted", "id", postgresql_where="deleted_at IS NULL"),
        Index("idx_user_email_active", "email", postgresql_where="deleted_at IS NULL AND is_active = true"),
    )

    @property
    def full_name(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.display_name or self.email.split("@")[0]


class ApiKey(Base):
    """API Key for programmatic access"""

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Key info
    name = Column(String(100), nullable=False)
    # SECURITY FIX: Increased from 64 to 72 chars to support bcrypt hashes (60 chars)
    key_hash = Column(String(72), unique=True, nullable=False, index=True)
    # PERF FIX: Added index on key_prefix for efficient bcrypt lookups
    key_prefix = Column(String(10), index=True)  # First 10 chars for identification

    # Permissions
    permissions = Column(JSONB, default=list)  # ["read", "write", "verify"]
    allowed_ips = Column(JSONB)  # IP whitelist if set
    rate_limit = Column(Integer, default=100)  # Requests per minute

    # Status
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime)

    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime)
    last_used_ip = Column(String(50))

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    # Table constraints
    __table_args__ = (
        CheckConstraint("rate_limit > 0", name="chk_apikey_rate_limit_positive"),
        CheckConstraint("usage_count >= 0", name="chk_apikey_usage_count_positive"),
        Index(
            "idx_apikey_user_name_unique",
            "user_id",
            "name",
            unique=True,
            postgresql_where="is_active = true",
        ),
    )
