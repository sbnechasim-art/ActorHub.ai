"""
Actor Pack API Endpoints
Training, downloading, and managing Actor Packs
"""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_api_key, get_current_user
from app.models.identity import ActorPack, Identity, TrainingStatus, UsageLog
from app.models.marketplace import License, PaymentStatus
from app.models.user import ApiKey, User
from app.schemas.identity import ActorPackCreate, ActorPackDownloadResponse, ActorPackResponse
from app.services.storage import StorageService
from app.services.training import TrainingService

router = APIRouter()

storage_service = StorageService()
training_service = TrainingService()


@router.post("/train", response_model=ActorPackResponse)
async def initiate_training(
    pack_data: ActorPackCreate,
    training_images: List[UploadFile] = File(..., description="Min 8 images required"),
    training_audio: Optional[List[UploadFile]] = File(
        None, description="Audio samples for voice cloning"
    ),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Initiate Actor Pack training for an identity.

    **Requirements:**
    - Minimum 8 face images from different angles
    - Optional: Audio samples (30+ seconds recommended)
    - Optional: Video samples for motion capture

    Training typically takes 15-30 minutes.
    """
    # Verify identity ownership
    result = await db.execute(
        select(Identity).where(
            Identity.user_id == current_user.id, Identity.display_name == pack_data.name
        )
    )
    identity = result.scalar_one_or_none()

    if not identity:
        raise HTTPException(404, "Identity not found")

    # Check if actor pack already exists
    existing_pack = await db.execute(select(ActorPack).where(ActorPack.identity_id == identity.id))
    if existing_pack.scalar_one_or_none():
        raise HTTPException(
            400, "Actor Pack already exists for this identity. Use update endpoint."
        )

    # Validate minimum images
    if len(training_images) < 8:
        raise HTTPException(400, "Minimum 8 training images required for quality results")

    import structlog
    logger = structlog.get_logger()

    # Validate image formats and sizes
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_AUDIO_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_IMAGE_HEADERS = {
        b'\xff\xd8\xff': 'image/jpeg',
        b'\x89PNG': 'image/png',
    }

    def is_valid_image(data: bytes) -> bool:
        for header in ALLOWED_IMAGE_HEADERS:
            if data[:len(header)] == header:
                return True
        return False

    # Upload training data with error handling
    uploaded_images = []
    try:
        for i, img in enumerate(training_images):
            img_bytes = await img.read()

            # Validate size
            if len(img_bytes) > MAX_IMAGE_SIZE:
                raise HTTPException(400, f"Image {i+1} exceeds 10MB limit")

            # Validate format
            if not is_valid_image(img_bytes):
                raise HTTPException(400, f"Image {i+1} has invalid format. Supported: JPEG, PNG")

            url = await storage_service.upload_file(
                file_bytes=img_bytes,
                filename=f"training/{identity.id}/{uuid.uuid4()}.jpg",
                content_type="image/jpeg",
            )
            uploaded_images.append(url)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to upload training images", error=str(e))
        # Cleanup any uploaded files
        for url in uploaded_images:
            try:
                await storage_service.delete_file(url)
            except Exception:
                pass
        raise HTTPException(500, f"Failed to upload training images: {str(e)}")

    uploaded_audio = []
    if training_audio:
        try:
            for i, audio in enumerate(training_audio):
                audio_bytes = await audio.read()

                # Validate size
                if len(audio_bytes) > MAX_AUDIO_SIZE:
                    raise HTTPException(400, f"Audio file {i+1} exceeds 50MB limit")

                url = await storage_service.upload_file(
                    file_bytes=audio_bytes,
                    filename=f"training/{identity.id}/{uuid.uuid4()}.wav",
                    content_type="audio/wav",
                )
                uploaded_audio.append(url)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to upload training audio", error=str(e))
            # Cleanup uploaded files
            for url in uploaded_images + uploaded_audio:
                try:
                    await storage_service.delete_file(url)
                except Exception:
                    pass
            raise HTTPException(500, f"Failed to upload training audio: {str(e)}")

    # Create Actor Pack record
    actor_pack = ActorPack(
        identity_id=identity.id,
        name=pack_data.name,
        description=pack_data.description,
        training_status=TrainingStatus.QUEUED,
        training_images_count=len(uploaded_images),
        training_audio_seconds=len(uploaded_audio) * 30,  # Estimate
        components={"face": True, "voice": len(uploaded_audio) > 0, "motion": False},
    )
    db.add(actor_pack)
    await db.commit()
    await db.refresh(actor_pack)

    # Queue training job (would use Celery in production)
    if background_tasks:
        background_tasks.add_task(
            training_service.train_actor_pack,
            actor_pack_id=str(actor_pack.id),
            image_urls=uploaded_images,
            audio_urls=uploaded_audio,
        )

    return actor_pack


@router.get("/status/{pack_id}", response_model=ActorPackResponse)
async def get_training_status(
    pack_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get Actor Pack training status"""
    actor_pack = await db.get(ActorPack, pack_id)

    if not actor_pack:
        raise HTTPException(404, "Actor Pack not found")

    # Verify ownership
    identity = await db.get(Identity, actor_pack.identity_id)
    if identity.user_id != current_user.id:
        raise HTTPException(403, "Access denied")

    return actor_pack


@router.get("/download/{identity_id}", response_model=ActorPackDownloadResponse)
async def download_actor_pack(
    identity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Download Actor Pack (requires valid license).

    Returns a signed URL valid for 1 hour.
    """
    # Check for valid license
    license_query = select(License).where(
        License.identity_id == identity_id,
        License.licensee_id == current_user.id,
        License.is_active.is_(True),
        License.payment_status == PaymentStatus.COMPLETED,
    )
    result = await db.execute(license_query)
    license = result.scalar_one_or_none()

    if not license:
        raise HTTPException(403, "No active license for this identity")

    # Check license validity
    if license.valid_until and license.valid_until < datetime.utcnow():
        raise HTTPException(403, "License has expired")

    # Get actor pack
    pack_query = select(ActorPack).where(
        ActorPack.identity_id == identity_id,
        ActorPack.training_status == "COMPLETED",  # Use string for VARCHAR column
    )
    result = await db.execute(pack_query)
    actor_pack = result.scalar_one_or_none()

    if not actor_pack:
        raise HTTPException(404, "Actor Pack not available")

    if not actor_pack.is_available:
        raise HTTPException(400, "Actor Pack is not currently available")

    # Generate signed download URL
    download_url = await storage_service.generate_presigned_url(
        bucket=actor_pack.s3_bucket, key=actor_pack.s3_key, expires_in=3600
    )

    # Log download
    usage_log = UsageLog(
        identity_id=identity_id,
        license_id=license.id,
        actor_pack_id=actor_pack.id,
        requester_id=current_user.id,
        requester_type="user",
        requester_name=current_user.full_name,
        action="download",
        result="allowed",
    )
    db.add(usage_log)

    # Update stats
    actor_pack.total_downloads += 1
    license.current_uses += 1

    await db.commit()

    return ActorPackDownloadResponse(
        download_url=download_url,
        expires_in_seconds=3600,
        file_size_mb=(
            actor_pack.file_size_bytes / (1024 * 1024) if actor_pack.file_size_bytes else 0
        ),
        version=actor_pack.version,
        components=actor_pack.components,
        checksum=actor_pack.checksum,
    )


@router.get("/public", response_model=List[ActorPackResponse])
async def list_public_actor_packs(
    category: Optional[str] = None,
    min_quality: Optional[float] = None,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """List publicly available Actor Packs"""
    stmt = select(ActorPack).where(
        ActorPack.is_public.is_(True),
        ActorPack.is_available.is_(True),
        ActorPack.training_status == "COMPLETED",  # Use string value for VARCHAR column
    )

    if min_quality:
        stmt = stmt.where(ActorPack.quality_score >= min_quality)

    stmt = stmt.order_by(ActorPack.total_downloads.desc())
    stmt = stmt.offset((page - 1) * limit).limit(limit)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/use/{pack_id}")
async def log_actor_pack_use(
    pack_id: uuid.UUID,
    usage_data: dict,
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey = Depends(get_api_key),
):
    """
    Log usage of an Actor Pack (called by integrations).

    This endpoint is used to track when Actor Packs are actually used
    in content generation, for billing and analytics.
    """
    actor_pack = await db.get(ActorPack, pack_id)
    if not actor_pack:
        raise HTTPException(404, "Actor Pack not found")

    # Log usage
    usage_log = UsageLog(
        identity_id=actor_pack.identity_id,
        actor_pack_id=pack_id,
        requester_id=api_key.user_id,
        requester_type="api",
        requester_name=api_key.name,
        api_key_id=api_key.id,
        action="generate",
        request_metadata=usage_data,
        result="allowed",
    )
    db.add(usage_log)

    # Update stats
    actor_pack.total_uses += 1

    # Calculate billing if applicable
    if usage_data.get("duration_seconds"):
        credits = usage_data["duration_seconds"] * actor_pack.price_per_second_usd
        usage_log.amount_charged_usd = credits
        actor_pack.total_revenue_usd += credits

    await db.commit()

    return {"status": "logged", "usage_id": str(usage_log.id)}
