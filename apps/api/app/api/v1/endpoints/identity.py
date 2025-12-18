"""
Identity API Endpoints
Core functionality for identity registration and verification
"""

import time
import uuid
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_api_key, get_current_user
from app.models.identity import Identity, IdentityStatus, ProtectionLevel, UsageLog
from app.models.user import ApiKey, User
from app.schemas.identity import (
    IdentityResponse,
    IdentityUpdate,
    VerifyRequest,
    VerifyResponse,
    VerifyResult,
)
from app.services.face_recognition import FaceRecognitionService
from app.services.storage import StorageService

router = APIRouter()

# Initialize services
face_service = FaceRecognitionService()
storage_service = StorageService()

# Allowed domains for image URLs (SSRF protection) - loaded from config
ALLOWED_IMAGE_DOMAINS = set(settings.ALLOWED_IMAGE_DOMAINS)


@router.post("/register", response_model=IdentityResponse)
async def register_identity(
    display_name: str = Form(..., description="Display name for the identity"),
    protection_level: str = Form("free", description="Protection level: free, pro, enterprise"),
    allow_commercial: bool = Form(False, description="Allow commercial use"),
    allow_ai_training: bool = Form(False, description="Allow AI training"),
    face_image: UploadFile = File(..., description="Primary face photo"),
    verification_image: UploadFile = File(..., description="Verification selfie"),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Register a new protected identity.

    **Requirements:**
    - Primary face photo (front-facing, good lighting)
    - Verification selfie (for liveness check)

    **Returns:** Identity record with protection status
    """
    import structlog
    logger = structlog.get_logger()

    logger.info(f"Starting identity registration for user {current_user.id}")
    logger.info(f"Display name: {display_name}, Protection level: {protection_level}")

    # Read images
    try:
        face_bytes = await face_image.read()
        verification_bytes = await verification_image.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded images: {str(e)}")
        raise HTTPException(400, "Failed to read uploaded images")

    logger.info(f"Face image size: {len(face_bytes)} bytes, Verification image size: {len(verification_bytes)} bytes")

    # Validate image sizes
    if len(face_bytes) > 10 * 1024 * 1024:  # 10MB limit
        logger.warning("Face image too large")
        raise HTTPException(400, "Face image too large (max 10MB)")
    if len(verification_bytes) > 10 * 1024 * 1024:
        logger.warning("Verification image too large")
        raise HTTPException(400, "Verification image too large (max 10MB)")

    # Validate image MIME types (check magic bytes)
    ALLOWED_IMAGE_HEADERS = {
        b'\xff\xd8\xff': 'image/jpeg',  # JPEG
        b'\x89PNG': 'image/png',         # PNG
        b'GIF87a': 'image/gif',          # GIF87
        b'GIF89a': 'image/gif',          # GIF89
        b'RIFF': 'image/webp',           # WebP
    }

    def get_image_type(data: bytes) -> str | None:
        for header, mime in ALLOWED_IMAGE_HEADERS.items():
            if data[:len(header)] == header:
                return mime
        # WebP check (RIFF + WEBP)
        if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            return 'image/webp'
        return None

    face_mime = get_image_type(face_bytes)
    if not face_mime:
        raise HTTPException(400, "Invalid face image format. Supported: JPEG, PNG, GIF, WebP")

    verification_mime = get_image_type(verification_bytes)
    if not verification_mime:
        raise HTTPException(400, "Invalid verification image format. Supported: JPEG, PNG, GIF, WebP")

    # Extract face embedding
    embedding = await face_service.extract_embedding(face_bytes)
    if embedding is None:
        raise HTTPException(
            400, "Could not detect face in image. Please use a clear, front-facing photo."
        )

    # Liveness check
    is_live = await face_service.liveness_check(verification_bytes)
    if not is_live:
        raise HTTPException(
            400, "Liveness check failed. Please take a new selfie with good lighting."
        )

    # Check for duplicates
    similar = await face_service.find_similar(
        embedding, threshold=settings.FACE_DUPLICATE_THRESHOLD
    )
    if similar:
        raise HTTPException(
            409, "This face is already registered. If this is your face, please contact support."
        )

    # Upload images to storage
    file_uuid = uuid.uuid4()
    face_filename = f"identities/{current_user.id}/{file_uuid}_face.jpg"
    face_image_url = await storage_service.upload_file(
        file_bytes=face_bytes,
        filename=face_filename,
        content_type="image/jpeg",
    )

    # Create identity record
    identity = Identity(
        user_id=current_user.id,
        display_name=display_name,
        profile_image_url=face_image_url,
        status=IdentityStatus.PROCESSING,
        protection_level=ProtectionLevel(protection_level),
        allow_commercial_use=allow_commercial,
        allow_ai_training=allow_ai_training,
    )
    db.add(identity)
    await db.flush()

    # Update identity status (embedding stored in Qdrant, not DB)
    # Note: face_embedding column skipped due to pgvector/asyncpg compatibility issue
    identity.status = IdentityStatus.VERIFIED
    identity.verified_at = datetime.utcnow()
    identity.verification_method = "selfie"

    try:
        logger.info("Committing identity to database...")
        # Commit to database first
        await db.commit()
        logger.info("Database commit successful")

        await db.refresh(identity)
        logger.info(f"Identity created with ID: {identity.id}")

        # Only after successful commit, store embedding in vector database
        logger.info("Registering embedding in Qdrant...")
        await face_service.register_embedding(identity.id, embedding)
        logger.info("Embedding registered successfully")
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Registration failed: {str(e)}")
        logger.error(f"Traceback: {error_details}")

        await db.rollback()
        # Clean up uploaded file on failure
        try:
            await storage_service.delete_file(face_filename)
        except Exception as cleanup_error:
            logger.warning(
                "Failed to cleanup uploaded file after registration failure",
                file=face_filename,
                cleanup_error=str(cleanup_error),
                original_error=str(e),
            )
        raise HTTPException(500, f"Failed to register identity: {str(e)}")

    return identity


@router.post("/verify", response_model=VerifyResponse)
async def verify_identity(
    request: VerifyRequest,
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey = Depends(get_api_key),
):
    """
    🔥 **CORE API ENDPOINT** - Called by AI platforms (Sora, Kling, etc.)

    Check if an image contains protected identities.

    **Input:** Image URL or base64 encoded image
    **Output:** Protection status and licensing options

    **Response time target:** <100ms
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())

    # Extract faces from input
    faces = []
    if request.image_base64:
        faces = await face_service.detect_faces_base64(request.image_base64)
    elif request.image_url:
        # Validate URL domain to prevent SSRF attacks
        parsed_url = urlparse(request.image_url)
        if parsed_url.netloc not in ALLOWED_IMAGE_DOMAINS:
            raise HTTPException(400, f"Image URL domain not allowed. Allowed domains: {', '.join(ALLOWED_IMAGE_DOMAINS)}")
        if parsed_url.scheme not in ("http", "https"):
            raise HTTPException(400, "Only HTTP/HTTPS URLs are allowed")
        faces = await face_service.detect_faces_url(request.image_url)
    else:
        raise HTTPException(400, "Must provide image_base64 or image_url")

    response_time_ms = int((time.time() - start_time) * 1000)

    if not faces:
        return VerifyResponse(
            protected=False,
            faces_detected=0,
            identities=[],
            message="No faces detected in image",
            response_time_ms=response_time_ms,
            request_id=request_id,
        )

    # Check each face against registry
    results = []
    any_protected = False

    for face in faces:
        embedding = face["embedding"]
        match = await face_service.find_match(
            embedding, threshold=settings.FACE_SIMILARITY_THRESHOLD
        )

        if match:
            any_protected = True
            identity = await db.get(Identity, uuid.UUID(match["identity_id"]))

            if identity:
                # Log this verification
                usage_log = UsageLog(
                    identity_id=identity.id,
                    requester_id=api_key.user_id,
                    requester_type="api",
                    requester_name=api_key.name,
                    api_key_id=api_key.id,
                    action="verify",
                    similarity_score=match["score"],
                    faces_detected=len(faces),
                    matched=True,
                    result="protected",
                    response_time_ms=response_time_ms,
                )
                db.add(usage_log)

                # Update identity stats
                identity.total_verifications += 1

                # Build license options
                license_options = []
                if identity.allow_commercial_use:
                    license_options = [
                        {
                            "type": "single_use",
                            "price_usd": identity.base_license_fee or 99,
                            "includes": "Single commercial use",
                        },
                        {
                            "type": "subscription",
                            "price_usd": (identity.base_license_fee or 99) * 3,
                            "duration_days": 30,
                            "includes": "Unlimited use for 30 days",
                        },
                    ]

                results.append(
                    VerifyResult(
                        protected=True,
                        identity_id=str(identity.id),
                        display_name=identity.display_name,
                        similarity_score=match["score"],
                        allow_commercial=identity.allow_commercial_use,
                        blocked_categories=identity.blocked_categories or [],
                        license_required=identity.allow_commercial_use,
                        license_options=(
                            license_options if request.include_license_options else None
                        ),
                        face_bbox=face.get("bbox"),
                    )
                )
            else:
                results.append(
                    VerifyResult(
                        protected=True,
                        identity_id=match["identity_id"],
                        similarity_score=match["score"],
                        license_required=True,
                        face_bbox=face.get("bbox"),
                    )
                )
        else:
            results.append(VerifyResult(protected=False, face_bbox=face.get("bbox")))

    await db.commit()

    return VerifyResponse(
        protected=any_protected,
        faces_detected=len(faces),
        identities=results,
        message="Protected identity detected" if any_protected else "No protected identities found",
        response_time_ms=int((time.time() - start_time) * 1000),
        request_id=request_id,
    )


@router.get("/mine", response_model=List[IdentityResponse])
async def get_my_identities(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all identities owned by the current user"""
    query = select(Identity).where(
        Identity.user_id == current_user.id, Identity.deleted_at.is_(None)
    )

    if status:
        query = query.where(Identity.status == status)

    query = query.order_by(Identity.created_at.desc())
    result = await db.execute(query)
    identities = result.scalars().all()

    return identities


@router.get("/{identity_id}", response_model=IdentityResponse)
async def get_identity(
    identity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific identity by ID"""
    identity = await db.get(Identity, identity_id)

    if not identity or identity.deleted_at:
        raise HTTPException(404, "Identity not found")

    # Only owner can view full details
    if identity.user_id != current_user.id:
        raise HTTPException(403, "Access denied")

    return identity


# Allowed fields that identity owners can update
ALLOWED_IDENTITY_UPDATE_FIELDS = {
    "display_name",
    "bio",
    "profile_image_url",
    "allow_commercial_use",
    "allow_ai_training",
    "allow_deepfake",
    "blocked_categories",
    "blocked_brands",
    "blocked_regions",
    "custom_restrictions",
    "base_license_fee",
    "hourly_rate",
    "per_image_rate",
    "revenue_share_percent",
}


@router.patch("/{identity_id}", response_model=IdentityResponse)
async def update_identity(
    identity_id: uuid.UUID,
    update_data: IdentityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update identity settings"""
    identity = await db.get(Identity, identity_id)

    if not identity or identity.deleted_at:
        raise HTTPException(404, "Identity not found")

    if identity.user_id != current_user.id:
        raise HTTPException(403, "Access denied")

    # Update fields - only allow specific fields (security: prevent status/protection_level manipulation)
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        if field not in ALLOWED_IDENTITY_UPDATE_FIELDS:
            raise HTTPException(400, f"Field '{field}' cannot be modified")
        setattr(identity, field, value)

    identity.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(identity)

    return identity


@router.delete("/{identity_id}")
async def delete_identity(
    identity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft delete an identity"""
    identity = await db.get(Identity, identity_id)

    if not identity or identity.deleted_at:
        raise HTTPException(404, "Identity not found")

    if identity.user_id != current_user.id:
        raise HTTPException(403, "Access denied")

    # Soft delete
    identity.deleted_at = datetime.utcnow()
    identity.status = IdentityStatus.SUSPENDED

    # Remove from vector database
    await face_service.delete_embedding(identity_id)

    await db.commit()

    return {"message": "Identity deleted successfully"}


@router.get("/{identity_id}/stats")
async def get_identity_stats(
    identity_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get usage statistics for an identity"""
    identity = await db.get(Identity, identity_id)

    if not identity:
        raise HTTPException(404, "Identity not found")

    if identity.user_id != current_user.id:
        raise HTTPException(403, "Access denied")

    # Get usage stats
    from datetime import timedelta

    from sqlalchemy import func

    since = datetime.utcnow() - timedelta(days=days)

    # Count verifications
    verifications_query = select(func.count(UsageLog.id)).where(
        UsageLog.identity_id == identity_id,
        UsageLog.action == "verify",
        UsageLog.created_at >= since,
    )
    verifications_result = await db.execute(verifications_query)
    verifications_count = verifications_result.scalar()

    # Count matches
    matches_query = select(func.count(UsageLog.id)).where(
        UsageLog.identity_id == identity_id,
        UsageLog.action == "verify",
        UsageLog.matched.is_(True),
        UsageLog.created_at >= since,
    )
    matches_result = await db.execute(matches_query)
    matches_count = matches_result.scalar()

    return {
        "identity_id": str(identity_id),
        "period_days": days,
        "total_verifications": verifications_count,
        "total_matches": matches_count,
        "total_licenses": identity.total_licenses,
        "total_revenue_usd": identity.total_revenue,
        "protection_level": identity.protection_level.value,
    }
