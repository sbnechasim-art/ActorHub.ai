"""
User and API Key Models
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
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

    # Role & Tier
    role = Column(Enum(UserRole), default=UserRole.USER)
    tier = Column(Enum(UserTier), default=UserTier.FREE)

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

    # Relationships
    identities = relationship("Identity", back_populates="user", lazy="dynamic")
    api_keys = relationship("ApiKey", back_populates="user", lazy="dynamic")
    purchases = relationship("License", foreign_keys="License.licensee_id", lazy="dynamic")

    @property
    def full_name(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.display_name or self.email.split("@")[0]


class ApiKey(Base):
    """API Key for programmatic access"""

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Key info
    name = Column(String(100), nullable=False)
    key_hash = Column(String(64), unique=True, nullable=False, index=True)
    key_prefix = Column(String(10))  # First 8 chars for identification

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
