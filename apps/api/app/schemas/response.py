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

    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED = "MISSING_REQUIRED"

    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    CONFLICT = "CONFLICT"

    # Rate limiting
    RATE_LIMITED = "RATE_LIMITED"

    # Server errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


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
