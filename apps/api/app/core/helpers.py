"""
Common Helper Functions

Reusable utilities for API endpoints to reduce code duplication.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional, TypeVar
from uuid import UUID

from fastapi import HTTPException, status

from app.schemas.response import ErrorCodes

T = TypeVar("T")


# ===========================================
# Timezone-aware datetime utilities
# ===========================================

def utc_now() -> datetime:
    """
    Get current UTC time as timezone-aware datetime.

    MEDIUM FIX: Always use this instead of datetime.utcnow() which returns
    naive datetime and is deprecated in Python 3.12+.

    Returns:
        datetime: Current UTC time with timezone info
    """
    return datetime.now(timezone.utc)


def utc_now_plus(days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0) -> datetime:
    """
    Get future UTC time as timezone-aware datetime.

    Args:
        days: Days to add
        hours: Hours to add
        minutes: Minutes to add
        seconds: Seconds to add

    Returns:
        datetime: Future UTC time with timezone info
    """
    return utc_now() + timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


def utc_now_minus(days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0) -> datetime:
    """
    Get past UTC time as timezone-aware datetime.

    Args:
        days: Days to subtract
        hours: Hours to subtract
        minutes: Minutes to subtract
        seconds: Seconds to subtract

    Returns:
        datetime: Past UTC time with timezone info
    """
    return utc_now() - timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


def get_or_404(
    entity: Optional[T],
    entity_name: str = "Resource",
    entity_id: Optional[UUID] = None,
) -> T:
    """
    Return entity if it exists, otherwise raise 404 HTTPException.

    Args:
        entity: The entity to check (from database query)
        entity_name: Human-readable name for error message (e.g., "Identity", "License")
        entity_id: Optional ID to include in error message for debugging

    Returns:
        The entity if it exists

    Raises:
        HTTPException: 404 if entity is None

    Example:
        identity = await db.get(Identity, identity_id)
        identity = get_or_404(identity, "Identity", identity_id)
    """
    if entity is None:
        detail = f"{entity_name} not found"
        if entity_id:
            detail = f"{entity_name} with ID {entity_id} not found"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )
    return entity


def check_ownership(
    entity: Any,
    user_id: UUID,
    owner_field: str = "user_id",
    entity_name: str = "resource",
) -> None:
    """
    Check if the current user owns the entity, raise 403 if not.

    Args:
        entity: The entity to check ownership of
        user_id: The current user's ID
        owner_field: The field name on entity that contains owner ID (default: "user_id")
        entity_name: Human-readable name for error message

    Raises:
        HTTPException: 403 if user doesn't own the entity

    Example:
        check_ownership(identity, current_user.id, entity_name="identity")
    """
    entity_owner_id = getattr(entity, owner_field, None)
    if entity_owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You don't have permission to access this {entity_name}",
        )


def get_owned_or_404(
    entity: Optional[T],
    user_id: UUID,
    entity_name: str = "Resource",
    owner_field: str = "user_id",
) -> T:
    """
    Combined check: entity exists AND user owns it.

    Args:
        entity: The entity to check
        user_id: The current user's ID
        entity_name: Human-readable name for error messages
        owner_field: The field name on entity that contains owner ID

    Returns:
        The entity if it exists and user owns it

    Raises:
        HTTPException: 404 if not found, 403 if not owned

    Example:
        identity = await db.get(Identity, identity_id)
        identity = get_owned_or_404(identity, current_user.id, "Identity")
    """
    entity = get_or_404(entity, entity_name)
    check_ownership(entity, user_id, owner_field, entity_name.lower())
    return entity


def require_verified(
    entity: Any,
    status_field: str = "status",
    verified_value: str = "VERIFIED",
    entity_name: str = "resource",
) -> None:
    """
    Require that an entity is verified.

    Args:
        entity: The entity to check
        status_field: The field name for status
        verified_value: The value that indicates verified status
        entity_name: Human-readable name for error message

    Raises:
        HTTPException: 400 if not verified
    """
    entity_status = getattr(entity, status_field, None)
    # Handle enum values
    if hasattr(entity_status, "value"):
        entity_status = entity_status.value

    if entity_status != verified_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{entity_name} is not verified",
        )


def require_active(
    entity: Any,
    active_field: str = "is_active",
    entity_name: str = "resource",
) -> None:
    """
    Require that an entity is active.

    Args:
        entity: The entity to check
        active_field: The field name for active status
        entity_name: Human-readable name for error message

    Raises:
        HTTPException: 400 if not active
    """
    is_active = getattr(entity, active_field, True)
    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{entity_name} is not active",
        )
