"""Identity and verification schemas"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import inspect as sa_inspect


class LivenessMetadata(BaseModel):
    """Metadata from live selfie capture for anti-spoofing verification"""

    # Accept both camelCase (from frontend) and snake_case
    model_config = ConfigDict(populate_by_name=True)

    capture_timestamp: int = Field(..., alias="captureTimestamp", description="Unix timestamp when selfie was captured")
    frame_count: int = Field(..., alias="frameCount", ge=1, description="Number of frames captured for liveness check")
    device_type: str = Field(..., alias="deviceType", description="Device type: 'desktop' or 'mobile'")
    camera_facing: str = Field(default="user", alias="cameraFacing", description="Camera facing mode: 'user' or 'environment'")

    def is_fresh(self, max_age_seconds: int = 30) -> bool:
        """Check if the capture is recent enough (within max_age_seconds)"""
        current_time = int(datetime.utcnow().timestamp() * 1000)
        age_ms = current_time - self.capture_timestamp
        return age_ms <= (max_age_seconds * 1000)


class IdentityCreate(BaseModel):
    """Schema for creating a new protected identity"""

    display_name: str = Field(..., min_length=1, max_length=255)
    protection_level: str = Field(default="free")
    allow_commercial_use: bool = False
    allow_ai_training: bool = False
    show_in_public_gallery: bool = False
    blocked_categories: List[str] = Field(default_factory=list)
    base_license_fee: float = Field(default=0, ge=0)


class IdentityUpdate(BaseModel):
    """Schema for updating identity settings.

    Note: protection_level cannot be changed via this endpoint.
    Contact support for protection level upgrades.
    """

    display_name: Optional[str] = None
    bio: Optional[str] = None
    # protection_level removed - not allowed to be modified by users
    allow_commercial_use: Optional[bool] = None
    allow_ai_training: Optional[bool] = None
    allow_deepfake: Optional[bool] = None
    show_in_public_gallery: Optional[bool] = None
    blocked_categories: Optional[List[str]] = None
    blocked_brands: Optional[List[str]] = None
    blocked_regions: Optional[List[str]] = None
    base_license_fee: Optional[float] = None
    hourly_rate: Optional[float] = None
    per_image_rate: Optional[float] = None


class ActorPackEmbedded(BaseModel):
    """Embedded Actor Pack info for identity response"""
    id: UUID
    training_status: str
    training_progress: int = 0
    training_error: Optional[str] = None
    training_started_at: Optional[datetime] = None
    training_completed_at: Optional[datetime] = None
    quality_score: Optional[float] = None
    authenticity_score: Optional[float] = None
    consistency_score: Optional[float] = None
    voice_quality_score: Optional[float] = None
    is_available: bool = False
    components: Optional[Dict[str, Any]] = None
    training_images_count: Optional[int] = None
    version: str = "1.0.0"

    class Config:
        from_attributes = True


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
    show_in_public_gallery: bool = False
    blocked_categories: Optional[List[str]] = None
    total_verifications: Optional[int] = 0
    total_licenses: Optional[int] = 0
    total_revenue: Optional[float] = 0.0
    created_at: datetime
    updated_at: datetime
    actor_pack: Optional[ActorPackEmbedded] = None

    @model_validator(mode="before")
    @classmethod
    def convert_none_to_defaults(cls, data):
        """Convert None values to default values"""
        if hasattr(data, "__dict__"):
            # ORM model - access attributes
            # Get actor_pack if relationship is loaded (without triggering lazy load)
            actor_pack_data = None

            # Use SQLAlchemy inspection to safely check if relationship is loaded
            try:
                insp = sa_inspect(data)
                # Check if actor_pack is in loaded attributes (not unloaded)
                if 'actor_pack' in insp.dict:
                    ap = insp.dict['actor_pack']
                    if ap is not None:
                        actor_pack_data = {
                            "id": ap.id,
                            "training_status": ap.training_status.value if hasattr(ap.training_status, 'value') else ap.training_status,
                            "training_progress": ap.training_progress or 0,
                            "training_error": ap.training_error,
                            "training_started_at": ap.training_started_at,
                            "training_completed_at": ap.training_completed_at,
                            "quality_score": ap.quality_score,
                            "authenticity_score": ap.authenticity_score,
                            "consistency_score": ap.consistency_score,
                            "voice_quality_score": ap.voice_quality_score,
                            "is_available": ap.is_available or False,
                            "components": ap.components,
                            "training_images_count": ap.training_images_count,
                            "version": ap.version or "1.0.0",
                        }
            except Exception:
                # If inspection fails, just skip actor_pack
                pass

            return {
                "id": data.id,
                "user_id": data.user_id,
                "display_name": data.display_name,
                "bio": data.bio,
                "profile_image_url": data.profile_image_url,
                "status": data.status.value if hasattr(data.status, 'value') else data.status,
                "verified_at": data.verified_at,
                "protection_level": data.protection_level.value if hasattr(data.protection_level, 'value') else data.protection_level,
                "allow_commercial_use": data.allow_commercial_use or False,
                "allow_ai_training": data.allow_ai_training or False,
                "show_in_public_gallery": data.show_in_public_gallery or False,
                "blocked_categories": data.blocked_categories,
                "total_verifications": data.total_verifications or 0,
                "total_licenses": data.total_licenses or 0,
                "total_revenue": data.total_revenue or 0.0,
                "created_at": data.created_at,
                "updated_at": data.updated_at,
                "actor_pack": actor_pack_data,
            }
        return data

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


# Import PaginationMeta from response module to avoid duplication
from app.schemas.response import PaginationMeta


class IdentityListResponse(BaseModel):
    """Paginated list of identities"""
    success: bool = True
    data: List[IdentityResponse]
    meta: PaginationMeta


class ActorPackListResponse(BaseModel):
    """Paginated list of actor packs"""
    success: bool = True
    data: List[ActorPackResponse]
    meta: PaginationMeta
