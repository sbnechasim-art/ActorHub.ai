"""
Pagination Utilities
Standardized pagination for all API endpoints

Provides:
- Consistent pagination parameters
- Offset/limit calculation
- Paginated response formatting
"""

from math import ceil
from typing import Any, Dict, Generic, List, Optional, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.core.config import settings

T = TypeVar("T")


# ===========================================
# Pagination Parameters
# ===========================================

class PaginationParams:
    """
    Standard pagination parameters.

    SECURITY FIX: Added maximum page limit to prevent DoS attacks.
    Without a limit, page=999999999 would cause expensive OFFSET operations.

    Usage in endpoint:
        async def list_items(pagination: PaginationParams = Depends()):
            ...
    """

    # Maximum page number to prevent DoS (500 pages * 100 limit = 50,000 items max)
    MAX_PAGE = settings.MAX_PAGE_NUMBER

    def __init__(
        self,
        page: int = Query(default=1, ge=1, le=settings.MAX_PAGE_NUMBER, description=f"Page number (1-indexed, max {settings.MAX_PAGE_NUMBER})"),
        limit: int = Query(default=settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE, description="Items per page"),
    ):
        # SECURITY: Enforce maximum page even if validator bypassed
        self.page = min(page, self.MAX_PAGE)
        self.limit = limit

    @property
    def offset(self) -> int:
        """Calculate offset for SQL query"""
        return (self.page - 1) * self.limit

    @property
    def skip(self) -> int:
        """Alias for offset"""
        return self.offset


class OffsetPaginationParams:
    """
    Alternative pagination using skip/limit.

    SECURITY FIX: Added maximum offset limit to prevent DoS attacks.
    Without a limit, attacker could request skip=999999999 causing
    expensive OFFSET operations on the database.

    Usage in endpoint:
        async def list_items(pagination: OffsetPaginationParams = Depends()):
            ...
    """

    # Maximum offset to prevent DoS (10,000 items = 500 pages of 20 items)
    MAX_OFFSET = settings.MAX_OFFSET

    def __init__(
        self,
        skip: int = Query(default=0, ge=0, le=settings.MAX_OFFSET, description=f"Number of items to skip (max {settings.MAX_OFFSET})"),
        limit: int = Query(default=settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE, description="Maximum items to return"),
    ):
        # SECURITY: Enforce maximum offset even if validator bypassed
        self.skip = min(skip, self.MAX_OFFSET)
        self.limit = limit

    @property
    def offset(self) -> int:
        """Alias for skip"""
        return self.skip

    @property
    def page(self) -> int:
        """Calculate page number (1-indexed)"""
        return (self.skip // self.limit) + 1 if self.limit > 0 else 1


# ===========================================
# Paginated Response Schema
# ===========================================

class PaginationMeta(BaseModel):
    """Pagination metadata for responses"""

    page: int
    limit: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper"""

    items: List[Any]
    meta: PaginationMeta

    class Config:
        arbitrary_types_allowed = True


# ===========================================
# Pagination Helper Functions
# ===========================================

def create_pagination_meta(
    page: int,
    limit: int,
    total: int,
) -> PaginationMeta:
    """Create pagination metadata"""
    total_pages = ceil(total / limit) if limit > 0 else 0

    return PaginationMeta(
        page=page,
        limit=limit,
        total=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


def paginated_response(
    items: List[Any],
    page: int,
    limit: int,
    total: int,
) -> Dict[str, Any]:
    """
    Create a standardized paginated response.

    Args:
        items: List of items for current page
        page: Current page number (1-indexed)
        limit: Items per page
        total: Total count of all items

    Returns:
        Dict with 'items' and 'meta' keys
    """
    meta = create_pagination_meta(page, limit, total)

    return {
        "items": items,
        "meta": {
            "page": meta.page,
            "limit": meta.limit,
            "total": meta.total,
            "total_pages": meta.total_pages,
            "has_next": meta.has_next,
            "has_prev": meta.has_prev,
        },
    }


async def paginate_query(
    db: AsyncSession,
    query: Select,
    pagination: PaginationParams,
    count_query: Optional[Select] = None,
) -> Dict[str, Any]:
    """
    Execute a query with pagination and return formatted response.

    Args:
        db: Database session
        query: SQLAlchemy select query
        pagination: Pagination parameters
        count_query: Optional custom count query

    Returns:
        Paginated response dict

    Usage:
        query = select(User).where(User.is_active == True)
        result = await paginate_query(db, query, pagination)
        return result
    """
    # Get total count
    if count_query is None:
        # Create count query from the main query
        count_query = select(func.count()).select_from(query.subquery())

    total = await db.scalar(count_query) or 0

    # Apply pagination to query
    paginated_query = query.offset(pagination.offset).limit(pagination.limit)
    result = await db.execute(paginated_query)
    items = list(result.scalars().all())

    return paginated_response(
        items=items,
        page=pagination.page,
        limit=pagination.limit,
        total=total,
    )


# ===========================================
# Cursor-Based Pagination (for large datasets)
# ===========================================

class CursorPaginationParams:
    """
    Cursor-based pagination for large datasets.

    More efficient than offset pagination for large tables.

    Usage:
        async def list_items(pagination: CursorPaginationParams = Depends()):
            ...
    """

    def __init__(
        self,
        cursor: Optional[str] = Query(default=None, description="Cursor for next page"),
        limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    ):
        self.cursor = cursor
        self.limit = limit


def cursor_paginated_response(
    items: List[Any],
    next_cursor: Optional[str],
    has_more: bool,
) -> Dict[str, Any]:
    """Create a cursor-based paginated response"""
    return {
        "items": items,
        "meta": {
            "next_cursor": next_cursor,
            "has_more": has_more,
            "count": len(items),
        },
    }
