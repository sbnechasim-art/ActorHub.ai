"""
Actor Pack API Endpoints
Training, downloading, and managing Actor Packs
"""

import json
import uuid
from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.helpers import utc_now  # MEDIUM FIX: Use timezone-aware datetime
from app.core.security import get_api_key, get_current_user
from app.models.identity import ActorPack, Identity, TrainingStatus, UsageLog
from app.models.marketplace import License, PaymentStatus
from app.models.user import ApiKey, User
from app.schemas.identity import ActorPackCreate, ActorPackDownloadResponse, ActorPackResponse
from app.core.config import settings
from app.services.storage import StorageService
from app.services.training import TrainingService
from app.core.helpers import get_or_404, check_ownership

# Import Celery task for async training
try:
    from celery import Celery
    celery_app = Celery('tasks', broker=settings.CELERY_BROKER_URL)
    # Import training task - will be available when worker is running
    train_actor_pack_task = celery_app.signature('tasks.training.train_actor_pack')
    CELERY_AVAILABLE = True
except Exception:
    CELERY_AVAILABLE = False
    train_actor_pack_task = None

logger = structlog.get_logger()
router = APIRouter()

storage_service = StorageService()
training_service = TrainingService()


@router.post("/train", response_model=ActorPackResponse, status_code=status.HTTP_201_CREATED)
async def initiate_training(
    pack_data: str = Form(..., description="JSON string with pack details"),
    training_images: List[UploadFile] = File(..., description="Min 8 images required"),
    training_audio: Optional[List[UploadFile]] = File(
        None, description="Audio samples for voice cloning"
    ),
    retrain: bool = Form(False, description="Set to true to replace existing Actor Pack"),
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

    **pack_data format (JSON string):**
    ```json
    {"name": "Identity Display Name", "description": "Optional description"}
    ```
    """
    # Parse pack_data from JSON string
    try:
        pack_data_dict = json.loads(pack_data)
        pack_data_obj = ActorPackCreate(**pack_data_dict)
    except json.JSONDecodeError:
        raise HTTPException(400, "pack_data must be a valid JSON string")
    except ValidationError as e:
        raise HTTPException(400, f"Invalid pack_data: {e.errors()}")

    # Verify identity ownership (exclude soft-deleted)
    # Use .first() to handle potential duplicates gracefully
    result = await db.execute(
        select(Identity).where(
            Identity.user_id == current_user.id,
            Identity.display_name == pack_data_obj.name,
            Identity.deleted_at.is_(None)
        ).order_by(Identity.created_at.asc())  # Get the oldest one
    )
    identity = result.scalars().first()
    identity = get_or_404(identity, "Identity")

    # Check if actor pack already exists
    existing_pack_result = await db.execute(select(ActorPack).where(ActorPack.identity_id == identity.id))
    existing_pack = existing_pack_result.scalar_one_or_none()
    if existing_pack:
        if not retrain:
            raise HTTPException(
                400, "Actor Pack already exists for this identity. Use retrain=true to replace."
            )
        # Delete old actor pack for retrain
        logger.info("Deleting existing Actor Pack for retrain",
                   pack_id=str(existing_pack.id), identity_id=str(identity.id))
        await db.delete(existing_pack)
        await db.flush()

    # Validate minimum images
    if len(training_images) < 8:
        raise HTTPException(400, "Minimum 8 training images required for quality results")

    # Validate image formats and sizes
    MAX_IMAGE_SIZE = settings.MAX_IMAGE_SIZE_BYTES  # 10MB from config
    MAX_AUDIO_SIZE = settings.MAX_AUDIO_SIZE_BYTES  # 50MB from config
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
        # SECURITY FIX: Log error details but don't expose to client
        logger.error("Failed to upload training images", error=str(e), exc_info=True)
        # Cleanup any uploaded files
        for url in uploaded_images:
            try:
                await storage_service.delete_file(url)
            except Exception:
                pass
        raise HTTPException(500, "Failed to upload training images. Please try again.")

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
            # SECURITY FIX: Log error details but don't expose to client
            logger.error("Failed to upload training audio", error=str(e), exc_info=True)
            # Cleanup uploaded files
            for url in uploaded_images + uploaded_audio:
                try:
                    await storage_service.delete_file(url)
                except Exception:
                    pass
            raise HTTPException(500, "Failed to upload training audio. Please try again.")

    # Create Actor Pack record
    actor_pack = ActorPack(
        identity_id=identity.id,
        name=pack_data_obj.name,
        description=pack_data_obj.description,
        training_status="QUEUED",
        training_images_count=len(uploaded_images),
        training_audio_seconds=len(uploaded_audio) * 30,  # Estimate
        components={"face": True, "voice": len(uploaded_audio) > 0, "motion": False},
    )
    db.add(actor_pack)
    await db.commit()
    await db.refresh(actor_pack)

    # Queue training job via Celery for distributed processing
    if CELERY_AVAILABLE:
        try:
            # Send to Celery worker queue
            celery_app.send_task(
                'tasks.training.train_actor_pack',
                args=[str(actor_pack.id), uploaded_images],
                kwargs={
                    'audio_urls': uploaded_audio if uploaded_audio else None,
                    'video_urls': None,
                    'trace_headers': None,
                },
                queue='training',
            )
            logger.info(
                "Training job queued to Celery",
                actor_pack_id=str(actor_pack.id),
                image_count=len(uploaded_images),
            )
        except Exception as e:
            logger.error("Failed to queue training job to Celery", error=str(e))
            # Update status to failed if we can't queue
            actor_pack.training_status = "FAILED"
            actor_pack.training_error = f"Failed to queue training: {str(e)}"
            await db.commit()
            await db.refresh(actor_pack)
    else:
        # Fallback warning - Celery not available
        logger.warning(
            "Celery not available, training will not be processed",
            actor_pack_id=str(actor_pack.id),
        )
        actor_pack.training_status = "FAILED"
        actor_pack.training_error = "Training service unavailable. Please try again later."
        await db.commit()
        await db.refresh(actor_pack)

    return actor_pack


@router.get("/status/{pack_id}", response_model=ActorPackResponse)
async def get_training_status(
    pack_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get Actor Pack training status"""
    actor_pack = await db.get(ActorPack, pack_id)
    actor_pack = get_or_404(actor_pack, "Actor Pack", pack_id)

    # Verify ownership via identity
    identity = await db.get(Identity, actor_pack.identity_id)
    check_ownership(identity, current_user.id, entity_name="Actor Pack")

    return actor_pack


@router.post("/poll-training/{pack_id}", response_model=ActorPackResponse)
async def poll_replicate_training(
    pack_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Poll Replicate for training status and update actor pack.

    Call this periodically while training_status is PROCESSING.
    """
    import httpx
    from app.core.config import settings

    actor_pack = await db.get(ActorPack, pack_id)
    actor_pack = get_or_404(actor_pack, "Actor Pack", pack_id)

    # Verify ownership
    identity = await db.get(Identity, actor_pack.identity_id)
    check_ownership(identity, current_user.id, entity_name="Actor Pack")

    # Check if we have a Replicate training ID stored
    if not actor_pack.lora_model_url or not actor_pack.lora_model_url.startswith("training:"):
        return actor_pack

    training_id = actor_pack.lora_model_url.replace("training:", "")

    # Poll Replicate
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"https://api.replicate.com/v1/trainings/{training_id}",
                headers={"Authorization": f"Token {settings.REPLICATE_API_TOKEN}"}
            )

            if response.status_code != 200:
                logger.warning(f"Failed to poll Replicate training: {response.status_code}")
                return actor_pack

            data = response.json()
            status = data.get("status")

            # Map Replicate status to our status
            if status == "succeeded":
                actor_pack.training_status = "COMPLETED"
                actor_pack.training_progress = 100
                actor_pack.is_available = True

                # Get the output LoRA weights URL
                output = data.get("output")
                if output:
                    if isinstance(output, dict) and "weights" in output:
                        actor_pack.lora_model_url = output["weights"]
                    elif isinstance(output, str):
                        actor_pack.lora_model_url = output

                logger.info(f"Training completed! LoRA: {actor_pack.lora_model_url}")

            elif status == "failed":
                actor_pack.training_status = "FAILED"
                actor_pack.training_error = data.get("error", "Training failed")
                logger.error(f"Training failed: {actor_pack.training_error}")

            elif status in ("starting", "processing"):
                actor_pack.training_status = "PROCESSING"
                # Estimate progress based on logs or time
                logs = data.get("logs", "")
                if "step" in logs.lower():
                    # Try to parse step progress
                    import re
                    matches = re.findall(r"step[:\s]*(\d+)", logs.lower())
                    if matches:
                        current_step = int(matches[-1])
                        # Assume 1000 steps total
                        actor_pack.training_progress = min(95, int(current_step / 10))
                elif actor_pack.training_progress < 90:
                    # Increment slowly
                    actor_pack.training_progress = min(90, actor_pack.training_progress + 5)

            await db.commit()
            await db.refresh(actor_pack)

    except Exception as e:
        logger.error(f"Error polling Replicate: {e}")

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
        License.payment_status == "COMPLETED",
    )
    result = await db.execute(license_query)
    license = result.scalar_one_or_none()

    if not license:
        raise HTTPException(403, "No active license for this identity")

    # Check license validity
    if license.valid_until and license.valid_until < utc_now():
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

    # Update stats atomically to prevent race conditions
    await db.execute(
        update(ActorPack)
        .where(ActorPack.id == actor_pack.id)
        .values(total_downloads=ActorPack.total_downloads + 1)
    )
    await db.execute(
        update(License)
        .where(License.id == license.id)
        .values(current_uses=License.current_uses + 1)
    )

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


@router.get("/download-own/{identity_id}", response_model=ActorPackDownloadResponse)
async def download_own_actor_pack(
    identity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Download your own Actor Pack (for identity owners).

    No license required - you own this identity.
    Returns a signed URL valid for 1 hour.
    """
    # Verify identity ownership
    identity = await db.get(Identity, identity_id)
    identity = get_or_404(identity, "Identity", identity_id)
    check_ownership(identity, current_user.id, entity_name="Identity")

    # Get actor pack
    pack_query = select(ActorPack).where(
        ActorPack.identity_id == identity_id,
        ActorPack.training_status == "COMPLETED",
    )
    result = await db.execute(pack_query)
    actor_pack = result.scalar_one_or_none()

    if not actor_pack:
        raise HTTPException(404, "Actor Pack not available. Training may still be in progress.")

    if not actor_pack.is_available:
        raise HTTPException(400, "Actor Pack is not currently available")

    # Check if we have the S3 file
    if not actor_pack.s3_bucket or not actor_pack.s3_key:
        raise HTTPException(404, "Actor Pack file not found. Please contact support.")

    # Generate signed download URL
    download_url = await storage_service.generate_presigned_url(
        bucket=actor_pack.s3_bucket,
        key=actor_pack.s3_key,
        expires_in=3600
    )

    # Log download
    usage_log = UsageLog(
        identity_id=identity_id,
        actor_pack_id=actor_pack.id,
        requester_id=current_user.id,
        requester_type="owner",
        requester_name=current_user.full_name,
        action="download_own",
        result="allowed",
    )
    db.add(usage_log)
    await db.commit()

    logger.info(
        "Owner downloaded actor pack",
        identity_id=str(identity_id),
        user_id=str(current_user.id),
        pack_id=str(actor_pack.id),
    )

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


@router.get("/mine", response_model=List[ActorPackResponse])
async def list_my_actor_packs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all Actor Packs for the current user's identities.

    Used for displaying training progress on the dashboard.
    Returns packs in all statuses (QUEUED, PROCESSING, COMPLETED, FAILED).
    """
    # Get user's identities
    identity_result = await db.execute(
        select(Identity.id).where(Identity.user_id == current_user.id)
    )
    identity_ids = [row[0] for row in identity_result.fetchall()]

    if not identity_ids:
        return []

    # Get actor packs for those identities
    stmt = select(ActorPack).where(
        ActorPack.identity_id.in_(identity_ids)
    ).order_by(ActorPack.created_at.desc())

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/cancel/{pack_id}")
async def cancel_training(
    pack_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cancel an in-progress training job.

    Can only cancel packs in QUEUED or PROCESSING status.

    **Returns:** Updated Actor Pack with FAILED status.

    **Errors:**
    - 400: Training cannot be cancelled (already completed/failed)
    - 403: Access denied (not your pack)
    - 404: Actor Pack not found
    """
    actor_pack = await db.get(ActorPack, pack_id)
    actor_pack = get_or_404(actor_pack, "Actor Pack", pack_id)

    # Get the identity to check ownership
    identity = await db.get(Identity, actor_pack.identity_id)
    if not identity or identity.user_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")

    # Can only cancel if in progress
    if actor_pack.training_status not in [TrainingStatus.QUEUED, TrainingStatus.PROCESSING]:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Cannot cancel training with status '{actor_pack.training_status}'. Only QUEUED or PROCESSING jobs can be cancelled."
        )

    # Update status
    actor_pack.training_status = TrainingStatus.FAILED
    actor_pack.training_error = "Cancelled by user"
    actor_pack.training_completed_at = utc_now()

    await db.commit()
    await db.refresh(actor_pack)

    logger.info(
        "Training cancelled by user",
        pack_id=str(pack_id),
        user_id=str(current_user.id)
    )

    return {
        "status": "cancelled",
        "message": "Training has been cancelled",
        "pack_id": str(pack_id)
    }


@router.delete("/{pack_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_actor_pack(
    pack_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete an Actor Pack.

    This performs a hard delete. Use with caution.

    **Returns:** 204 No Content on success.

    **Errors:**
    - 400: Cannot delete pack with active licenses
    - 403: Access denied (not your pack)
    - 404: Actor Pack not found
    """
    actor_pack = await db.get(ActorPack, pack_id)
    actor_pack = get_or_404(actor_pack, "Actor Pack", pack_id)

    # Get the identity to check ownership
    identity = await db.get(Identity, actor_pack.identity_id)
    if not identity or identity.user_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")

    # Check for active licenses
    active_licenses = await db.execute(
        select(License).where(
            License.identity_id == actor_pack.identity_id,
            License.is_active == True
        )
    )
    if active_licenses.scalars().first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot delete Actor Pack with active licenses. Please wait for licenses to expire."
        )

    # Delete usage logs first
    await db.execute(
        select(UsageLog).where(UsageLog.actor_pack_id == pack_id)
    )

    # Delete the pack
    await db.delete(actor_pack)
    await db.commit()

    logger.info(
        "Actor Pack deleted",
        pack_id=str(pack_id),
        user_id=str(current_user.id)
    )

    return None


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
    actor_pack = get_or_404(actor_pack, "Actor Pack", pack_id)

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

    # Update stats atomically to prevent race conditions
    update_values = {"total_uses": ActorPack.total_uses + 1}

    # Calculate billing if applicable
    if usage_data.get("duration_seconds"):
        credits = usage_data["duration_seconds"] * actor_pack.price_per_second_usd
        usage_log.amount_charged_usd = credits
        update_values["total_revenue_usd"] = ActorPack.total_revenue_usd + credits

    await db.execute(
        update(ActorPack)
        .where(ActorPack.id == actor_pack.id)
        .values(**update_values)
    )

    await db.commit()

    return {"status": "logged", "usage_id": str(usage_log.id)}
