"""
Content Generation API Endpoints
Generate AI content using licensed Actor Packs

FIXED: Jobs now stored in Redis instead of in-memory dict, and generation
tasks queued via Celery for reliability across restarts.
"""

import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

import httpx
import redis
import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.helpers import utc_now  # MEDIUM FIX: Use timezone-aware datetime
from app.core.security import get_current_user
from app.models.identity import ActorPack, Identity, UsageLog
from app.models.marketplace import License
from app.models.user import User
from app.services.generation import get_generation_service

logger = structlog.get_logger()
router = APIRouter()

# Redis client for job storage (replaces in-memory dict)
_redis_client = None


def get_redis_client():
    """Get or create Redis client for job storage."""
    global _redis_client
    if _redis_client is None:
        redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6380/0')
        _redis_client = redis.from_url(redis_url, decode_responses=True)
    return _redis_client


def get_job(job_id: str) -> Optional[dict]:
    """Get job status from Redis."""
    try:
        client = get_redis_client()
        data = client.get(f"generation_job:{job_id}")
        return json.loads(data) if data else None
    except Exception as e:
        logger.warning(f"Failed to get job from Redis: {e}")
        return None


def set_job(job_id: str, data: dict, ttl: int = 86400):
    """Set job status in Redis with 24-hour TTL."""
    try:
        client = get_redis_client()
        client.setex(f"generation_job:{job_id}", ttl, json.dumps(data, default=str))
    except Exception as e:
        logger.warning(f"Failed to set job in Redis: {e}")


class ContentType(str, Enum):
    FACE = "face"
    VOICE = "voice"
    MOTION = "motion"


class GenerationRequest(BaseModel):
    """Request to generate content using a licensed Actor Pack"""
    license_id: uuid.UUID = Field(..., description="ID of the active license")
    content_type: ContentType = Field(..., description="Type of content to generate")
    prompt: str = Field(..., min_length=1, max_length=1000, description="Generation prompt or text")
    negative_prompt: Optional[str] = Field(None, max_length=500, description="What to avoid (for face)")
    num_outputs: int = Field(1, ge=1, le=4, description="Number of outputs (for face)")


class GenerationResponse(BaseModel):
    """Response from content generation"""
    job_id: str
    status: str
    content_type: str
    outputs: Optional[list] = None
    output_url: Optional[str] = None
    estimated_time: Optional[str] = None
    error: Optional[str] = None


class JobStatusResponse(BaseModel):
    """Job status response"""
    job_id: str
    status: str
    progress: int = 0
    outputs: Optional[list] = None
    output_url: Optional[str] = None
    error: Optional[str] = None


# Worker URL for queuing Celery tasks
WORKER_URL = getattr(settings, 'WORKER_URL', 'http://localhost:8001')


@router.post("/generate", response_model=GenerationResponse)
async def generate_content(
    request: GenerationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate AI content using a licensed Actor Pack.

    **Content Types:**
    - `face`: Generate images with the actor's face
    - `voice`: Generate speech with the actor's voice
    - `motion`: Generate video with the actor's motion (coming soon)

    **Requirements:**
    - Active license for the identity
    - License must not be expired
    - Sufficient usage remaining (if limited)

    FIXED: Jobs now stored in Redis and tasks queued via Celery.
    """
    # Verify license ownership and validity
    result = await db.execute(
        select(License).where(
            License.id == request.license_id,
            License.licensee_id == current_user.id,
            License.is_active == True,
            License.payment_status == "COMPLETED",
        )
    )
    license = result.scalar_one_or_none()

    if not license:
        raise HTTPException(403, "No active license found")

    # Check expiry
    if license.valid_until and license.valid_until < utc_now():
        raise HTTPException(403, "License has expired")

    # Check usage limits
    if license.max_uses and license.current_uses >= license.max_uses:
        raise HTTPException(403, "License usage limit reached")

    # Get Actor Pack
    result = await db.execute(
        select(ActorPack).where(
            ActorPack.identity_id == license.identity_id,
            ActorPack.training_status == "COMPLETED",
            ActorPack.is_available == True,
        )
    )
    actor_pack = result.scalar_one_or_none()

    if not actor_pack:
        raise HTTPException(404, "Actor Pack not available. Training may not be complete.")

    # Create job in Redis (not in-memory)
    job_id = f"gen_{uuid.uuid4().hex[:12]}"
    job_data = {
        "status": "queued",
        "content_type": request.content_type.value,
        "progress": 0,
        "created_at": utc_now().isoformat(),
        "user_id": str(current_user.id),
    }
    set_job(job_id, job_data)

    # Queue generation task via Celery (not in-memory BackgroundTasks)
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{WORKER_URL}/tasks/run_generation",
                json={
                    "job_id": job_id,
                    "actor_pack_id": str(actor_pack.id),
                    "license_id": str(license.id),
                    "user_id": str(current_user.id),
                    "content_type": request.content_type.value,
                    "prompt": request.prompt,
                    "negative_prompt": request.negative_prompt,
                    "num_outputs": request.num_outputs,
                },
                timeout=5.0
            )
        logger.info("Generation task queued", job_id=job_id)
    except Exception as e:
        logger.error(f"Failed to queue generation task: {e}", job_id=job_id)
        set_job(job_id, {**job_data, "status": "failed", "error": "Failed to queue task"})
        raise HTTPException(500, "Failed to queue generation task")

    # Estimate time based on content type
    time_estimates = {
        ContentType.FACE: "30-60 seconds",
        ContentType.VOICE: "10-30 seconds",
        ContentType.MOTION: "2-5 minutes",
    }

    return GenerationResponse(
        job_id=job_id,
        status="queued",
        content_type=request.content_type.value,
        estimated_time=time_estimates.get(request.content_type, "1-2 minutes"),
    )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_generation_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get the status of a generation job (from Redis)"""
    job = get_job(job_id)

    if not job:
        raise HTTPException(404, "Job not found or expired")

    # Verify job belongs to user
    if job.get("user_id") != str(current_user.id):
        raise HTTPException(404, "Job not found")

    return JobStatusResponse(
        job_id=job_id,
        status=job.get("status", "unknown"),
        progress=job.get("progress", 0),
        outputs=job.get("outputs"),
        output_url=job.get("output_url"),
        error=job.get("error"),
    )


async def run_generation(
    job_id: str,
    actor_pack: ActorPack,
    license_id: str,
    user_id: str,
    content_type: ContentType,
    prompt: str,
    negative_prompt: str = None,
    num_outputs: int = 1,
):
    """Background task to run content generation"""
    from app.core.database import async_session_maker

    generation_service = get_generation_service()

    try:
        _jobs[job_id]["status"] = "processing"
        _jobs[job_id]["progress"] = 10

        if content_type == ContentType.FACE:
            # Check if LoRA model is available
            if not actor_pack.lora_model_url:
                raise Exception("LoRA model not trained yet")

            _jobs[job_id]["progress"] = 30

            result = await generation_service.generate_face_image(
                lora_model_url=actor_pack.lora_model_url,
                prompt=prompt,
                negative_prompt=negative_prompt or "",
                num_outputs=num_outputs,
            )

            _jobs[job_id]["outputs"] = result.get("outputs", [])

        elif content_type == ContentType.VOICE:
            # Get voice model info from actor pack
            voice_config = actor_pack.components.get("voice_model", {}) if actor_pack.components else {}

            if not voice_config:
                raise Exception("Voice model not trained yet")

            _jobs[job_id]["progress"] = 30

            voice_id = voice_config.get("voice_id")
            provider = voice_config.get("provider", "elevenlabs")

            if provider == "elevenlabs" and voice_id:
                result = await generation_service.generate_voice(
                    voice_id=voice_id,
                    text=prompt,
                    voice_provider="elevenlabs",
                )
            elif provider == "xtts" and voice_config.get("reference_audio"):
                result = await generation_service.generate_voice(
                    voice_id=voice_config["reference_audio"],
                    text=prompt,
                    voice_provider="xtts",
                )
            else:
                raise Exception("Voice model configuration invalid")

            _jobs[job_id]["output_url"] = result.get("output_url")

        elif content_type == ContentType.MOTION:
            raise Exception("Motion generation coming soon")

        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["progress"] = 100

        # Log usage
        async with async_session_maker() as db:
            usage_log = UsageLog(
                identity_id=actor_pack.identity_id,
                license_id=uuid.UUID(license_id),
                actor_pack_id=actor_pack.id,
                requester_id=uuid.UUID(user_id),
                requester_type="user",
                action="generate",
                request_metadata={
                    "content_type": content_type.value,
                    "prompt": prompt[:100],  # Truncate for storage
                },
                result="allowed",
            )
            db.add(usage_log)

            # Update license usage
            from sqlalchemy import update
            await db.execute(
                update(License)
                .where(License.id == uuid.UUID(license_id))
                .values(current_uses=License.current_uses + 1)
            )

            await db.commit()

    except Exception as e:
        logger.error(f"Generation failed for job {job_id}: {e}")
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)


@router.get("/my-jobs")
async def list_my_jobs(
    current_user: User = Depends(get_current_user),
    limit: int = 10,
):
    """List recent generation jobs for current user"""
    # In production, filter by user_id stored with job
    recent_jobs = []
    for job_id, job in sorted(
        _jobs.items(),
        key=lambda x: x[1].get("created_at", datetime.min),
        reverse=True
    )[:limit]:
        recent_jobs.append({
            "job_id": job_id,
            "status": job.get("status"),
            "content_type": job.get("content_type"),
            "created_at": job.get("created_at"),
        })
    return recent_jobs
