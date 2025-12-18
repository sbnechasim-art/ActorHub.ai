"""Identity and verification schemas"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class IdentityCreate(BaseModel):
    """Schema for creating a new protected identity"""

    display_name: str = Field(..., min_length=1, max_length=255)
    protection_level: str = Field(default="free")
    allow_commercial_use: bool = False
    allow_ai_training: bool = False
    blocked_categories: List[str] = Field(default_factory=list)
    base_license_fee: float = Field(default=0, ge=0)


class IdentityUpdate(BaseModel):
    """Schema for updating identity settings"""

    display_name: Optional[str] = None
    bio: Optional[str] = None
    protection_level: Optional[str] = None
    allow_commercial_use: Optional[bool] = None
    allow_ai_training: Optional[bool] = None
    allow_deepfake: Optional[bool] = None
    blocked_categories: Optional[List[str]] = None
    blocked_brands: Optional[List[str]] = None
    blocked_regions: Optional[List[str]] = None
    base_license_fee: Optional[float] = None
    hourly_rate: Optional[float] = None
    per_image_rate: Optional[float] = None


class IdentityResponse(BaseModel):
    """Schema for identity response"""

    id: UUID
    user_id: UUID
    display_name: str
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None
    status: str
    verified_at: Optional[datetime] = None
    protection_level: str
    allow_commercial_use: bool = False
    allow_ai_training: bool = False
    blocked_categories: Optional[List[str]] = None
    total_verifications: int = 0
    total_licenses: int = 0
    total_revenue: float = 0.0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VerifyRequest(BaseModel):
    """
    Request to verify if image contains protected identities.
    This is the core API endpoint for platforms like Sora/Kling.
    """

    image_url: Optional[str] = Field(None, description="URL of image to check")
    image_base64: Optional[str] = Field(None, description="Base64 encoded image")
    video_url: Optional[str] = Field(None, description="URL of video to check")
    check_all_frames: bool = Field(default=False, description="Check all video frames")
    include_license_options: bool = Field(default=True)


class VerifyResult(BaseModel):
    """Result for a single detected face"""

    protected: bool
    identity_id: Optional[str] = None
    display_name: Optional[str] = None
    similarity_score: Optional[float] = None
    allow_commercial: Optional[bool] = None
    blocked_categories: Optional[List[str]] = None
    license_required: bool = False
    license_options: Optional[List[Dict[str, Any]]] = None
    face_bbox: Optional[List[float]] = None  # [x1, y1, x2, y2]


class VerifyResponse(BaseModel):
    """
    Response from identity verification.
    Fast response for integration with AI generation platforms.
    """

    protected: bool
    faces_detected: int
    identities: List[VerifyResult]
    message: str
    response_time_ms: int
    request_id: str


class ActorPackCreate(BaseModel):
    """Schema for initiating Actor Pack training"""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    training_images_urls: List[str] = Field(default_factory=list)
    training_audio_urls: List[str] = Field(default_factory=list)
    training_video_urls: List[str] = Field(default_factory=list)
    include_voice: bool = True
    include_motion: bool = False


class ActorPackResponse(BaseModel):
    """Schema for Actor Pack response"""

    id: UUID
    identity_id: UUID
    name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    training_status: str = "pending"
    training_progress: int = 0
    quality_score: Optional[float] = None
    components: Optional[Dict[str, Any]] = None
    is_available: bool = False
    total_downloads: int = 0
    total_uses: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ActorPackDownloadResponse(BaseModel):
    """Response with download URL for Actor Pack"""

    download_url: str
    expires_in_seconds: int
    file_size_mb: float
    version: str
    components: Dict[str, Any]
    checksum: Optional[str]
