"""Pydantic schemas for request/response validation"""

# Admin schemas
from app.schemas.admin import (
    AdminDashboardStats,
    AuditLogEntry,
    SystemMetrics,
    UserSummary,
)

# Analytics schemas
from app.schemas.analytics import (
    DashboardAnalytics,
    IdentityAnalytics,
    RevenueStats,
    TimeSeriesPoint,
    UsageStats,
)

# Auth schemas
from app.schemas.auth import (
    EmailVerificationRequest,
    Enable2FAResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    Verify2FALogin,
    Verify2FARequest,
)

# GDPR schemas
from app.schemas.gdpr import (
    ConsentUpdate,
    DataExportRequest,
    DeleteAccountRequest,
)

# Identity schemas
from app.schemas.identity import (
    ActorPackCreate,
    ActorPackResponse,
    IdentityCreate,
    IdentityResponse,
    IdentityUpdate,
    VerifyRequest,
    VerifyResponse,
    VerifyResult,
)

# Marketplace schemas
from app.schemas.marketplace import (
    CheckoutSessionResponse,
    LicenseCreate,
    LicenseResponse,
    ListingCreate,
    ListingResponse,
)

# Notification schemas
from app.schemas.notification import (
    NotificationListResponse,
    NotificationPreferences,
    NotificationResponse,
)

# Refund schemas
from app.schemas.refund import (
    RefundEligibility,
    RefundRequest,
    RefundResponse,
    RefundStatusResponse,
)

# Subscription schemas
from app.schemas.subscription import (
    CheckoutResponse,
    CreateCheckoutRequest,
    PlanInfo,
    SubscriptionPlanType,
    SubscriptionResponse,
)

# Response schemas
from app.schemas.response import (
    ErrorCodes,
    ErrorDetail,
    ErrorResponse,
    PaginatedResponse,
    PaginationMeta,
    SuccessResponse,
    create_error_response,
    create_paginated_response,
    create_success_response,
)

# User schemas
from app.schemas.user import (
    ApiKeyCreate,
    ApiKeyResponse,
    DashboardStats,
    MessageResponse,
    StatusResponse,
    TokenResponse,
    TwoFactorPendingResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)

__all__ = [
    # Response
    "ErrorCodes",
    "ErrorDetail",
    "ErrorResponse",
    "PaginatedResponse",
    "PaginationMeta",
    "SuccessResponse",
    "create_error_response",
    "create_paginated_response",
    "create_success_response",
    # Admin
    "AdminDashboardStats",
    "AuditLogEntry",
    "SystemMetrics",
    "UserSummary",
    # Analytics
    "DashboardAnalytics",
    "IdentityAnalytics",
    "RevenueStats",
    "TimeSeriesPoint",
    "UsageStats",
    # Auth
    "EmailVerificationRequest",
    "Enable2FAResponse",
    "PasswordResetConfirm",
    "PasswordResetRequest",
    "Verify2FALogin",
    "Verify2FARequest",
    # GDPR
    "ConsentUpdate",
    "DataExportRequest",
    "DeleteAccountRequest",
    # Identity
    "ActorPackCreate",
    "ActorPackResponse",
    "IdentityCreate",
    "IdentityResponse",
    "IdentityUpdate",
    "VerifyRequest",
    "VerifyResponse",
    "VerifyResult",
    # Marketplace
    "CheckoutSessionResponse",
    "LicenseCreate",
    "LicenseResponse",
    "ListingCreate",
    "ListingResponse",
    # Notification
    "NotificationListResponse",
    "NotificationPreferences",
    "NotificationResponse",
    # Refund
    "RefundEligibility",
    "RefundRequest",
    "RefundResponse",
    "RefundStatusResponse",
    # Subscription
    "CheckoutResponse",
    "CreateCheckoutRequest",
    "PlanInfo",
    "SubscriptionPlanType",
    "SubscriptionResponse",
    # User
    "ApiKeyCreate",
    "ApiKeyResponse",
    "DashboardStats",
    "MessageResponse",
    "StatusResponse",
    "TokenResponse",
    "TwoFactorPendingResponse",
    "UserCreate",
    "UserResponse",
    "UserUpdate",
]
