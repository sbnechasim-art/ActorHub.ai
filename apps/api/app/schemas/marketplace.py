"""Marketplace schemas"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class LicenseCreate(BaseModel):
    """Schema for purchasing a license"""

    identity_id: UUID
    license_type: str = Field(
        ...,
        pattern="^(single_use|subscription|unlimited|custom)$",
        description="License type: single_use, subscription, unlimited, custom"
    )
    usage_type: str = Field(
        ...,
        pattern="^(personal|commercial|editorial|educational)$",
        description="Usage type: personal, commercial, editorial, educational"
    )
    duration_days: int = Field(default=30, ge=1, le=365, description="License duration (1-365 days)")
    project_name: Optional[str] = Field(None, max_length=255)
    project_description: Optional[str] = Field(None, max_length=2000)
    allowed_platforms: List[str] = Field(default_factory=list, max_length=20)
    max_impressions: Optional[int] = Field(None, ge=0, le=1_000_000_000)
    max_outputs: Optional[int] = Field(None, ge=0, le=1_000_000)


class LicenseResponse(BaseModel):
    """Schema for license response"""

    id: UUID
    identity_id: UUID
    licensee_id: UUID
    license_type: str
    usage_type: str
    project_name: Optional[str]
    valid_from: datetime
    valid_until: Optional[datetime]
    is_active: bool
    price_usd: float
    payment_status: str
    current_uses: int
    max_outputs: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class LicensePriceRequest(BaseModel):
    """Request for license pricing"""

    identity_id: UUID
    license_type: str = Field(..., pattern="^(single_use|subscription|unlimited|custom)$")
    usage_type: str = Field(..., pattern="^(personal|commercial|editorial|educational)$")
    duration_days: int = Field(default=30, ge=1, le=365, description="License duration (1-365 days)")
    max_impressions: Optional[int] = Field(None, ge=0, le=1_000_000_000)
    max_outputs: Optional[int] = Field(None, ge=0, le=1_000_000)


class LicensePriceResponse(BaseModel):
    """Response with license pricing breakdown"""

    base_price: float
    duration_multiplier: float
    usage_multiplier: float
    platform_fee: float
    total_price: float
    currency: str = "USD"
    breakdown: Dict[str, float]


class ListingCreate(BaseModel):
    """Schema for creating a marketplace listing"""

    identity_id: UUID
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    category: str = Field(default="actor")
    tags: List[str] = Field(default_factory=list)
    pricing_tiers: List[Dict[str, Any]] = Field(default_factory=list)
    requires_approval: bool = False


class ListingUpdate(BaseModel):
    """Schema for updating a listing"""

    title: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    pricing_tiers: Optional[List[Dict[str, Any]]] = None
    is_active: Optional[bool] = None
    requires_approval: Optional[bool] = None


class ListingResponse(BaseModel):
    """Schema for listing response"""

    id: UUID
    identity_id: UUID
    title: str
    slug: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    preview_images: List[str] = []
    category: Optional[str] = None
    tags: List[str] = []
    pricing_tiers: List[Dict[str, Any]] = []
    is_active: bool = True
    is_featured: bool = False
    view_count: int = 0
    license_count: int = 0
    avg_rating: Optional[float] = None
    rating_count: int = 0
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def convert_none_to_empty_lists(cls, data):
        """Convert None values to empty lists for array fields"""
        if hasattr(data, "__dict__"):
            # ORM model - access attributes
            return {
                "id": data.id,
                "identity_id": data.identity_id,
                "title": data.title,
                "slug": data.slug,
                "description": data.description,
                "short_description": data.short_description,
                "thumbnail_url": data.thumbnail_url,
                "preview_images": data.preview_images if data.preview_images is not None else [],
                "category": data.category,
                "tags": data.tags if data.tags is not None else [],
                "pricing_tiers": data.pricing_tiers if data.pricing_tiers is not None else [],
                "is_active": data.is_active,
                "is_featured": data.is_featured,
                "view_count": data.view_count or 0,
                "license_count": data.license_count or 0,
                "avg_rating": data.avg_rating,
                "rating_count": data.rating_count or 0,
                "created_at": data.created_at,
            }
        elif isinstance(data, dict):
            # Dict input
            data["preview_images"] = data.get("preview_images") or []
            data["tags"] = data.get("tags") or []
            data["pricing_tiers"] = data.get("pricing_tiers") or []
            return data
        return data

    class Config:
        from_attributes = True


class ListingSearchParams(BaseModel):
    """Parameters for searching listings"""

    query: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_rating: Optional[float] = None
    sort_by: str = Field(default="popular")  # popular, newest, price_low, price_high
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class CheckoutSessionResponse(BaseModel):
    """Response for Stripe checkout session"""

    checkout_url: str
    session_id: str
    price_usd: float
    license_details: Dict[str, Any]
