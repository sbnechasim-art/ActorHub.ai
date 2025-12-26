"""
Standardized API Response Schemas

All API responses should follow these patterns for consistency:

Success Response:
{
    "success": true,
    "data": { ... },
    "meta": { "page": 1, "limit": 20, "total": 100 }  // for paginated
}

Error Response:
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Email is invalid",
        "details": { "field": "email", "reason": "format" }
    }
}
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Pagination metadata"""

    page: int = Field(ge=1, description="Current page number")
    limit: int = Field(ge=1, le=100, description="Items per page")
    total: int = Field(ge=0, description="Total number of items")
    total_pages: int = Field(ge=0, description="Total number of pages")
    has_next: bool = Field(description="Whether there are more pages")
    has_prev: bool = Field(description="Whether there are previous pages")

    @classmethod
    def create(cls, page: int, limit: int, total: int) -> "PaginationMeta":
        """Factory method to create pagination meta from params"""
        total_pages = (total + limit - 1) // limit if limit > 0 else 0
        return cls(
            page=page,
            limit=limit,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )


class ErrorDetail(BaseModel):
    """Error detail structure"""

    code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional error details"
    )


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response wrapper"""

    success: bool = True
    data: T
    meta: Optional[Dict[str, Any]] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response wrapper"""

    success: bool = True
    data: List[T]
    meta: PaginationMeta


class ErrorResponse(BaseModel):
    """Standard error response wrapper"""

    success: bool = False
    error: ErrorDetail


# Common error codes
class ErrorCodes:
    """Standard error codes for API responses"""

    # Authentication & Authorization
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_PASSWORD = "INVALID_PASSWORD"
    ACCOUNT_DISABLED = "ACCOUNT_DISABLED"

    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED = "MISSING_REQUIRED"
    INVALID_FORMAT = "INVALID_FORMAT"

    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    CONFLICT = "CONFLICT"
    DUPLICATE_IDENTITY = "DUPLICATE_IDENTITY"  # Face already registered
    IDENTITY_NOT_FOUND = "IDENTITY_NOT_FOUND"
    LICENSE_NOT_FOUND = "LICENSE_NOT_FOUND"

    # Payment errors
    PAYMENT_ERROR = "PAYMENT_ERROR"
    PAYMENT_NOT_CONFIGURED = "PAYMENT_NOT_CONFIGURED"
    INVALID_PLAN = "INVALID_PLAN"
    FREE_PLAN_CHECKOUT = "FREE_PLAN_CHECKOUT"
    REFUND_FAILED = "REFUND_FAILED"
    REFUND_WINDOW_EXPIRED = "REFUND_WINDOW_EXPIRED"
    REFUND_LIMIT_EXCEEDED = "REFUND_LIMIT_EXCEEDED"
    PAYOUT_FAILED = "PAYOUT_FAILED"
    STRIPE_ACCOUNT_REQUIRED = "STRIPE_ACCOUNT_REQUIRED"

    # Identity & verification errors
    LIVENESS_CHECK_FAILED = "LIVENESS_CHECK_FAILED"
    FACE_NOT_DETECTED = "FACE_NOT_DETECTED"
    FACE_QUALITY_LOW = "FACE_QUALITY_LOW"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    IDENTITY_NOT_VERIFIED = "IDENTITY_NOT_VERIFIED"
    COMMERCIAL_USE_DENIED = "COMMERCIAL_USE_DENIED"

    # Rate limiting
    RATE_LIMITED = "RATE_LIMITED"
    EXPORT_RATE_LIMITED = "EXPORT_RATE_LIMITED"

    # Subscription errors
    NO_ACTIVE_SUBSCRIPTION = "NO_ACTIVE_SUBSCRIPTION"
    SUBSCRIPTION_LIMIT_REACHED = "SUBSCRIPTION_LIMIT_REACHED"
    API_CALLS_EXCEEDED = "API_CALLS_EXCEEDED"
    IDENTITIES_LIMIT_EXCEEDED = "IDENTITIES_LIMIT_EXCEEDED"

    # GDPR errors
    DELETION_PENDING = "DELETION_PENDING"
    EXPORT_IN_PROGRESS = "EXPORT_IN_PROGRESS"
    AGE_VERIFICATION_REQUIRED = "AGE_VERIFICATION_REQUIRED"
    UNDERAGE_USER = "UNDERAGE_USER"

    # Server errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    DATABASE_ERROR = "DATABASE_ERROR"
    STORAGE_ERROR = "STORAGE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"


def create_error_response(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Helper function to create error response dict"""
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
    }


def create_success_response(
    data: Any,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Helper function to create success response dict"""
    response = {"success": True, "data": data}
    if meta:
        response["meta"] = meta
    return response


def create_paginated_response(
    data: List[Any],
    page: int,
    limit: int,
    total: int,
) -> Dict[str, Any]:
    """Helper function to create paginated response dict"""
    return {
        "success": True,
        "data": data,
        "meta": PaginationMeta.create(page, limit, total).model_dump(),
    }


# ===========================================
# Standardized Error Messages
# ===========================================

class ErrorMessages:
    """Standardized error messages for consistency across the API."""

    # Authentication
    NOT_AUTHENTICATED = "Authentication required. Please log in."
    INVALID_CREDENTIALS = "Invalid email or password."
    INVALID_TOKEN = "Invalid or expired token."
    SESSION_EXPIRED = "Session expired. Please log in again."
    PASSWORD_CHANGED = "Session expired due to password change. Please log in again."
    ACCOUNT_DISABLED = "Your account has been disabled. Contact support."
    TWO_FA_REQUIRED = "Two-factor authentication required."
    INVALID_2FA_CODE = "Invalid verification code."

    # Authorization
    FORBIDDEN = "You don't have permission to perform this action."
    NOT_OWNER = "You don't have permission to access this resource."
    ADMIN_REQUIRED = "Administrator access required."
    VERIFIED_REQUIRED = "Email verification required."

    # Resource errors
    NOT_FOUND = "{resource} not found."
    ALREADY_EXISTS = "{resource} already exists."
    CONFLICT = "Operation conflicts with current state."

    # Identity
    IDENTITY_NOT_FOUND = "Identity not found."
    IDENTITY_NOT_VERIFIED = "Identity is not verified."
    DUPLICATE_FACE = "A similar face is already registered."
    FACE_NOT_DETECTED = "No face detected in the image."
    FACE_QUALITY_LOW = "Image quality too low. Please use a clearer photo."
    LIVENESS_FAILED = "Liveness check failed. Please try again."

    # License
    LICENSE_NOT_FOUND = "License not found."
    LICENSE_EXPIRED = "License has expired."
    LICENSE_INACTIVE = "License is not active."
    LICENSE_LIMIT_REACHED = "License usage limit reached."
    NO_ACTIVE_LICENSE = "No active license found."

    # Payment
    PAYMENT_FAILED = "Payment failed. Please try again."
    PAYMENT_NOT_CONFIGURED = "Payment system not configured."
    REFUND_FAILED = "Refund failed. Please contact support."
    REFUND_WINDOW_EXPIRED = "Refund window has expired ({days} days)."
    REFUND_LIMIT_EXCEEDED = "Maximum refund limit ({limit}) reached."
    STRIPE_ACCOUNT_REQUIRED = "Stripe account setup required for payouts."
    PAYOUT_MINIMUM = "Minimum payout amount is ${amount}."

    # Rate limiting
    RATE_LIMITED = "Too many requests. Please wait {seconds} seconds."
    EXPORT_RATE_LIMITED = "Export already in progress. Please wait."

    # Subscription
    SUBSCRIPTION_REQUIRED = "Active subscription required."
    SUBSCRIPTION_LIMIT = "Your plan limit has been reached."
    API_CALLS_EXCEEDED = "API call limit exceeded for your plan."
    IDENTITIES_LIMIT = "Identity limit exceeded for your plan."

    # GDPR
    DELETION_PENDING = "Account deletion already scheduled."
    AGE_REQUIRED = "Age verification required."
    UNDERAGE = "You must be 18 or older to use this service."

    # Validation
    INVALID_INPUT = "Invalid input provided."
    REQUIRED_FIELD = "Field '{field}' is required."
    INVALID_FORMAT = "Invalid format for '{field}'."
    MIN_LENGTH = "{field} must be at least {length} characters."
    MAX_LENGTH = "{field} cannot exceed {length} characters."
    FILE_TOO_LARGE = "File size exceeds maximum ({max_mb} MB)."
    INVALID_FILE_TYPE = "Invalid file type. Allowed: {types}."

    # Server errors
    INTERNAL_ERROR = "An unexpected error occurred. Please try again."
    SERVICE_UNAVAILABLE = "Service temporarily unavailable."
    DATABASE_ERROR = "Database error. Please try again."
    STORAGE_ERROR = "Storage error. Please try again."
    EXTERNAL_ERROR = "External service error. Please try again."


def api_error(
    status_code: int,
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> None:
    """
    Raise an HTTPException with standardized error format.

    Args:
        status_code: HTTP status code (400, 401, 403, 404, 500, etc.)
        code: Error code from ErrorCodes class
        message: Human-readable message from ErrorMessages or custom
        details: Additional error details (optional)
        headers: Optional HTTP headers to include

    Raises:
        HTTPException with standardized error response

    Example:
        from app.schemas.response import api_error, ErrorCodes, ErrorMessages

        api_error(404, ErrorCodes.NOT_FOUND, ErrorMessages.NOT_FOUND.format(resource="Identity"))
    """
    from fastapi import HTTPException

    content = create_error_response(code, message, details)

    raise HTTPException(
        status_code=status_code,
        detail=content["error"],
        headers=headers,
    )
