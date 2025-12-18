"""
Data models for ActorHub SDK
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class LicenseType(str, Enum):
    """Available license types"""
    SINGLE_USE = "single_use"
    SUBSCRIPTION = "subscription"
    UNLIMITED = "unlimited"


class UsageType(str, Enum):
    """How the identity can be used"""
    COMMERCIAL = "commercial"
    PERSONAL = "personal"
    EDITORIAL = "editorial"
    EDUCATIONAL = "educational"


class Identity(BaseModel):
    """Represents a protected identity"""
    id: str
    display_name: str
    allow_commercial: bool = False
    blocked_categories: List[str] = Field(default_factory=list)
    license_options: List[Dict[str, Any]] = Field(default_factory=list)
    similarity_score: float = 0.0


class VerifyResult(BaseModel):
    """Result for a single detected face"""
    protected: bool
    identity_id: Optional[str] = None
    display_name: Optional[str] = None
    similarity_score: Optional[float] = None
    allow_commercial: Optional[bool] = None
    blocked_categories: List[str] = Field(default_factory=list)
    license_required: bool = False
    license_options: Optional[List[Dict[str, Any]]] = None
    face_bbox: Optional[List[float]] = None


class VerifyResponse(BaseModel):
    """Response from identity verification"""
    protected: bool
    faces_detected: int
    identities: List[VerifyResult]
    message: str
    response_time_ms: int = 0
    request_id: str = ""


class License(BaseModel):
    """Represents a purchased license"""
    id: str
    identity_id: str
    license_type: str
    usage_type: str
    valid_from: datetime
    valid_until: Optional[datetime] = None
    price_usd: float
    is_active: bool = True


class ActorPack(BaseModel):
    """Represents an Actor Pack"""
    id: str
    identity_id: str
    name: str
    version: str
    components: Dict[str, bool]
    quality_score: Optional[float] = None
    download_url: Optional[str] = None
    file_size_mb: Optional[float] = None


class PriceBreakdown(BaseModel):
    """License price breakdown"""
    base_price: float
    duration_multiplier: float
    usage_multiplier: float
    platform_fee: float
    total_price: float
    currency: str = "USD"
    breakdown: Dict[str, float] = Field(default_factory=dict)
