"""
Identity API Endpoints
Core functionality for identity registration and verification
"""

import json
import time
import traceback
import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import urlparse

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.helpers import utc_now  # MEDIUM FIX: Use timezone-aware datetime
from app.core.database import get_db
from app.core.security import get_api_key, get_current_user
from app.models.identity import ActorPack, Identity, IdentityStatus, ProtectionLevel, UsageLog
from app.models.user import ApiKey, User
from app.schemas.identity import (
    IdentityListResponse,
    IdentityResponse,
    IdentityUpdate,
    LivenessMetadata,
    VerifyRequest,
    VerifyResponse,
    VerifyResult,
)
from app.schemas.response import PaginationMeta
from app.core.helpers import get_or_404, check_ownership, get_owned_or_404
from sqlalchemy import func
from app.services.face_recognition import FaceRecognitionService
from app.services.storage import StorageService
from app.services.listing import ListingService

logger = structlog.get_logger()
router = APIRouter()

# Initialize services
face_service = FaceRecognitionService()
storage_service = StorageService()

# Allowed domains for image URLs (SSRF protection) - loaded from config
ALLOWED_IMAGE_DOMAINS = set(settings.ALLOWED_IMAGE_DOMAINS)


@router.post("/register", response_model=IdentityResponse, status_code=status.HTTP_201_CREATED)
async def register_identity(
    display_name: str = Form(..., description="Display name for the identity"),
    protection_level: str = Form("free", description="Protection level: free, pro, enterprise"),
    allow_commercial: bool = Form(False, description="Allow commercial use"),
    allow_ai_training: bool = Form(False, description="Allow AI training"),
    show_in_public_gallery: bool = Form(False, description="Show in public gallery"),
    face_image: UploadFile = File(..., description="Primary face photo"),
    verification_image: UploadFile = File(..., description="Verification selfie"),
    is_live_capture: str = Form("false", description="Whether selfie was captured live from camera"),
    liveness_metadata: Optional[str] = Form(None, description="JSON metadata from live capture"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Register a new protected identity.

    **Requirements:**
    - Primary face photo (front-facing, good lighting)
    - Verification selfie (for liveness check) - preferably live camera capture

    **Returns:** 201 Created with identity record and protection status.

    **Errors:**
    - 400: Invalid image, no face detected, face verification failed, or stale capture
    - 401: Unauthorized
    - 422: Validation error
    """
    # Bind user context for all logs in this request
    bound_logger = logger.bind(
        user_id=str(current_user.id),
        endpoint="identity.register"
    )

    bound_logger.info(
        "Starting identity registration",
        display_name=display_name,
        protection_level=protection_level
    )

    # Parse and validate liveness metadata if provided
    parsed_liveness: Optional[LivenessMetadata] = None
    is_live = is_live_capture.lower() == "true"

    if is_live and liveness_metadata:
        try:
            liveness_data = json.loads(liveness_metadata)
            parsed_liveness = LivenessMetadata(**liveness_data)

            # Validate timestamp freshness (within 60 seconds to allow for processing)
            if not parsed_liveness.is_fresh(max_age_seconds=60):
                bound_logger.warning("Selfie capture is too old", capture_timestamp=parsed_liveness.capture_timestamp)
                raise HTTPException(
                    400,
                    "Selfie capture has expired. Please take a new selfie."
                )

            bound_logger.info(
                "Liveness metadata validated",
                device_type=parsed_liveness.device_type,
                frame_count=parsed_liveness.frame_count,
                capture_age_ms=int(utc_now().timestamp() * 1000) - parsed_liveness.capture_timestamp
            )
        except json.JSONDecodeError:
            bound_logger.warning("Invalid liveness metadata JSON")
            raise HTTPException(400, "Invalid liveness metadata format")
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            bound_logger.warning("Failed to parse liveness metadata", error=str(e))
            # Continue without liveness metadata if parsing fails

    # Read images
    try:
        face_bytes = await face_image.read()
        verification_bytes = await verification_image.read()
    except Exception as e:
        bound_logger.error("Failed to read uploaded images", error=str(e))
        raise HTTPException(400, "Failed to read uploaded images")

    bound_logger.info(
        "Images received",
        face_image_size=len(face_bytes),
        verification_image_size=len(verification_bytes)
    )

    # Validate image sizes
    if len(face_bytes) > 10 * 1024 * 1024:  # 10MB limit
        bound_logger.warning("Face image too large", size=len(face_bytes))
        raise HTTPException(400, "Face image too large (max 10MB)")
    if len(verification_bytes) > 10 * 1024 * 1024:
        bound_logger.warning("Verification image too large", size=len(verification_bytes))
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

    # CRITICAL SECURITY CHECK: Verify face_image and verification_image are the SAME person
    # This prevents attackers from registering someone else's face with their own selfie
    verification_embedding = await face_service.extract_embedding(verification_bytes)
    if verification_embedding is None:
        raise HTTPException(
            400, "Could not detect face in verification selfie. Please use a clear, front-facing photo."
        )

    # Compare face embeddings using the service (handles mock mode properly)
    is_match, face_similarity = await face_service.compare_faces(
        embedding, verification_embedding, settings.FACE_SIMILARITY_THRESHOLD
    )

    if not is_match:
        logger.warning(
            f"Face verification FAILED: similarity {face_similarity:.3f} < threshold {settings.FACE_SIMILARITY_THRESHOLD}"
        )
        raise HTTPException(
            400,
            "Face verification failed. The face in your photo does not match your verification selfie. "
            "Please ensure both images show the same person."
        )

    logger.info(f"Face verification PASSED: similarity {face_similarity:.3f}")

    # Check for duplicates
    similar = await face_service.find_similar(
        embedding, threshold=settings.FACE_DUPLICATE_THRESHOLD
    )
    if similar:
        raise HTTPException(
            409, "This face is already registered. If this is your face, please contact support."
        )

    # Clean up soft-deleted identities with same name (hard delete)
    from sqlalchemy import select, delete
    from app.models.marketplace import Listing
    from app.models.identity import UsageLog

    deleted_identity_result = await db.execute(
        select(Identity).where(
            Identity.user_id == current_user.id,
            Identity.display_name == display_name.strip(),
            Identity.deleted_at.isnot(None)
        )
    )
    deleted_identities = deleted_identity_result.scalars().all()

    for deleted_identity in deleted_identities:
        bound_logger.info(
            "Cleaning up soft-deleted identity with same name",
            deleted_identity_id=str(deleted_identity.id),
            display_name=display_name
        )
        # Delete related records first
        await db.execute(delete(UsageLog).where(UsageLog.identity_id == deleted_identity.id))
        await db.execute(delete(Listing).where(Listing.identity_id == deleted_identity.id))
        await db.execute(delete(ActorPack).where(ActorPack.identity_id == deleted_identity.id))
        await db.delete(deleted_identity)

    if deleted_identities:
        await db.flush()
        bound_logger.info(f"Cleaned up {len(deleted_identities)} soft-deleted identities")

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
        status="PROCESSING",
        protection_level=protection_level.upper(),  # Store as string
        allow_commercial_use=allow_commercial,
        allow_ai_training=allow_ai_training,
        show_in_public_gallery=show_in_public_gallery,
    )
    db.add(identity)
    await db.flush()

    # Update identity status (embedding stored in Qdrant, not DB)
    # Note: face_embedding column skipped due to pgvector/asyncpg compatibility issue
    identity.status = "VERIFIED"
    identity.verified_at = utc_now()
    identity.verification_method = "live_selfie" if is_live else "selfie"
    identity.verification_data = {
        "face_similarity_score": round(face_similarity, 4),
        "similarity_threshold": settings.FACE_SIMILARITY_THRESHOLD,
        "verification_passed": True,
        "is_live_capture": is_live,
        "liveness_metadata": parsed_liveness.model_dump() if parsed_liveness else None,
    }

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

        # Auto-create marketplace listing if conditions are met
        if identity.allow_commercial_use and identity.show_in_public_gallery:
            try:
                listing_service = ListingService(db)
                listing = await listing_service.create_basic_listing(identity)
                if listing:
                    await db.commit()
                    logger.info("Auto-created marketplace listing", listing_id=str(listing.id))
            except Exception as listing_error:
                # Don't fail the registration if listing creation fails
                logger.warning("Failed to auto-create listing", error=str(listing_error))
    except Exception as e:
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
        # SECURITY FIX: Don't expose internal error details to client
        raise HTTPException(500, "Failed to register identity. Please try again.")

    return identity


@router.get("/gallery", response_model=IdentityListResponse)
async def get_public_gallery(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all verified identities that opted into the public gallery.

    This endpoint is public and does not require authentication.
    Returns identities with their profile images for browsing.
    """
    # Base query for filtering
    base_query = select(Identity).where(
        Identity.show_in_public_gallery == True,
        Identity.status == "VERIFIED",
        Identity.deleted_at.is_(None),
    )

    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply pagination
    offset = (page - 1) * limit
    query = base_query.order_by(Identity.verified_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    identities = result.scalars().all()

    return IdentityListResponse(
        success=True,
        data=[IdentityResponse.model_validate(i) for i in identities],
        meta=PaginationMeta.create(page=page, limit=limit, total=total),
    )


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


@router.get("/mine", response_model=IdentityListResponse)
async def get_my_identities(
    status: Optional[str] = None,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all identities owned by the current user"""
    logger.info(f"GET /identity/mine - user_id={current_user.id}, email={current_user.email}, status_filter={status}")

    base_query = select(Identity).options(
        selectinload(Identity.actor_pack)
    ).where(
        Identity.user_id == current_user.id, Identity.deleted_at.is_(None)
    )

    if status:
        base_query = base_query.where(Identity.status == status)

    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply pagination
    offset = (page - 1) * limit
    query = base_query.order_by(Identity.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    identities = result.scalars().all()

    logger.info(f"GET /identity/mine - returning {len(identities)} identities (total={total})")

    return IdentityListResponse(
        success=True,
        data=[IdentityResponse.model_validate(i) for i in identities],
        meta=PaginationMeta.create(page=page, limit=limit, total=total),
    )


@router.get("/{identity_id}", response_model=IdentityResponse)
async def get_identity(
    identity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific identity by ID, including actor pack training status"""
    from app.models.identity import ActorPack

    # Load identity with actor_pack relation
    stmt = (
        select(Identity)
        .where(Identity.id == identity_id)
        .options(selectinload(Identity.actor_pack))
    )
    result = await db.execute(stmt)
    identity = result.scalar_one_or_none()

    # Treat soft-deleted as not found
    if identity and identity.deleted_at:
        identity = None

    identity = get_owned_or_404(identity, current_user.id, "Identity")
    return identity


# Allowed fields that identity owners can update
ALLOWED_IDENTITY_UPDATE_FIELDS = {
    "display_name",
    "bio",
    "profile_image_url",
    "allow_commercial_use",
    "allow_ai_training",
    "allow_deepfake",
    "show_in_public_gallery",
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

    # Treat soft-deleted as not found
    if identity and identity.deleted_at:
        identity = None

    identity = get_owned_or_404(identity, current_user.id, "Identity")

    # Update fields - only allow specific fields (security: prevent status/protection_level manipulation)
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        if field not in ALLOWED_IDENTITY_UPDATE_FIELDS:
            raise HTTPException(400, f"Field '{field}' cannot be modified")
        setattr(identity, field, value)

    identity.updated_at = utc_now()

    # Check if listing settings changed and update marketplace listing accordingly
    listing_fields_changed = any(
        field in update_dict for field in ['allow_commercial_use', 'show_in_public_gallery']
    )
    if listing_fields_changed:
        try:
            listing_service = ListingService(db)
            await listing_service.update_or_create_listing(identity)
        except Exception as listing_error:
            logger.warning("Failed to update marketplace listing", error=str(listing_error))

    await db.commit()
    await db.refresh(identity)

    return identity


@router.delete("/{identity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_identity(
    identity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Soft delete an identity.

    **Returns:** 204 No Content on success.

    **Errors:**
    - 401: Unauthorized
    - 403: Access denied (not your identity)
    - 404: Identity not found
    """
    identity = await db.get(Identity, identity_id)

    # Treat soft-deleted as not found
    if identity and identity.deleted_at:
        identity = None

    identity = get_owned_or_404(identity, current_user.id, "Identity")

    # Soft delete
    identity.deleted_at = utc_now()
    identity.status = "SUSPENDED"

    # Remove from vector database
    await face_service.delete_embedding(identity_id)

    # Deactivate marketplace listing
    from sqlalchemy import select
    from app.models.marketplace import Listing

    listing_result = await db.execute(
        select(Listing).where(
            Listing.identity_id == identity_id,
            Listing.is_active.is_(True)
        )
    )
    listing = listing_result.scalar_one_or_none()
    if listing:
        listing.is_active = False
        listing.updated_at = utc_now()
        logger.info(
            "Deactivated listing for deleted identity",
            identity_id=str(identity_id),
            listing_id=str(listing.id)
        )

    await db.commit()

    return None


@router.get("/{identity_id}/stats")
async def get_identity_stats(
    identity_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get usage statistics for an identity"""
    identity = await db.get(Identity, identity_id)
    identity = get_owned_or_404(identity, current_user.id, "Identity")

    # Get usage stats
    since = utc_now() - timedelta(days=days)

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
