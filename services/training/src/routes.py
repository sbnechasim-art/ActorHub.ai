"""Training Service API Routes."""

import structlog
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

from .config import get_settings, Settings
from .tasks import start_training_job, cancel_training_job

router = APIRouter(tags=["training"])
logger = structlog.get_logger()


class TrainingStatus(str, Enum):
    PENDING = "pending"
    PREPROCESSING = "preprocessing"
    TRAINING = "training"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TrainingRequest(BaseModel):
    """Training job request."""
    actor_pack_id: str = Field(..., description="Actor pack ID")
    user_id: str = Field(..., description="User ID")
    image_urls: list[str] = Field(..., min_length=5, max_length=20, description="Training image URLs")
    trigger_word: str = Field(default="ACTOR", description="Trigger word for the model")
    training_steps: int = Field(default=1000, ge=500, le=3000, description="Number of training steps")
    learning_rate: float = Field(default=1e-4, description="Learning rate")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for status updates")


class TrainingJob(BaseModel):
    """Training job details."""
    job_id: str
    actor_pack_id: str
    user_id: str
    status: TrainingStatus
    progress: float
    created_at: datetime
    updated_at: datetime
    model_url: Optional[str] = None
    error_message: Optional[str] = None


class TrainingStatusResponse(BaseModel):
    """Training status response."""
    job_id: str
    status: TrainingStatus
    progress: float
    eta_seconds: Optional[int] = None
    model_url: Optional[str] = None
    error_message: Optional[str] = None


def get_settings_dep() -> Settings:
    return get_settings()


# In-memory job storage (use Redis in production)
training_jobs: dict[str, TrainingJob] = {}


@router.post("/jobs", response_model=TrainingJob)
async def create_training_job(
    request: TrainingRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings_dep),
):
    """
    Create a new training job for an actor pack.

    This will:
    1. Validate and preprocess training images
    2. Upload images to S3
    3. Start training on Replicate
    4. Return job ID for status tracking
    """
    logger.info(
        "Creating training job",
        actor_pack_id=request.actor_pack_id,
        user_id=request.user_id,
        num_images=len(request.image_urls),
    )

    # Validate image count
    if len(request.image_urls) < settings.min_images_per_pack:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum {settings.min_images_per_pack} images required",
        )

    if len(request.image_urls) > settings.max_images_per_pack:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.max_images_per_pack} images allowed",
        )

    # Create job
    job_id = str(uuid.uuid4())
    now = datetime.utcnow()

    job = TrainingJob(
        job_id=job_id,
        actor_pack_id=request.actor_pack_id,
        user_id=request.user_id,
        status=TrainingStatus.PENDING,
        progress=0,
        created_at=now,
        updated_at=now,
    )

    training_jobs[job_id] = job

    # Start training in background
    background_tasks.add_task(
        start_training_job,
        job_id=job_id,
        request=request,
        settings=settings,
    )

    logger.info("Training job created", job_id=job_id)
    return job


@router.get("/jobs/{job_id}", response_model=TrainingStatusResponse)
async def get_training_status(job_id: str):
    """Get training job status."""
    if job_id not in training_jobs:
        raise HTTPException(status_code=404, detail="Training job not found")

    job = training_jobs[job_id]

    # Estimate ETA based on progress
    eta_seconds = None
    if job.status == TrainingStatus.TRAINING and job.progress > 0:
        # Rough estimate: assume 20 minutes total training time
        total_time = 1200
        elapsed = total_time * job.progress
        eta_seconds = int(total_time - elapsed)

    return TrainingStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        eta_seconds=eta_seconds,
        model_url=job.model_url,
        error_message=job.error_message,
    )


@router.post("/jobs/{job_id}/cancel")
async def cancel_training(
    job_id: str,
    background_tasks: BackgroundTasks,
):
    """Cancel a training job."""
    if job_id not in training_jobs:
        raise HTTPException(status_code=404, detail="Training job not found")

    job = training_jobs[job_id]

    if job.status in [TrainingStatus.COMPLETED, TrainingStatus.FAILED, TrainingStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Job already finished")

    # Cancel in background
    background_tasks.add_task(cancel_training_job, job_id)

    job.status = TrainingStatus.CANCELLED
    job.updated_at = datetime.utcnow()

    logger.info("Training job cancelled", job_id=job_id)
    return {"message": "Training job cancelled", "job_id": job_id}


@router.get("/jobs", response_model=list[TrainingJob])
async def list_training_jobs(
    user_id: Optional[str] = None,
    status: Optional[TrainingStatus] = None,
    limit: int = 20,
    offset: int = 0,
):
    """List training jobs with optional filters."""
    jobs = list(training_jobs.values())

    if user_id:
        jobs = [j for j in jobs if j.user_id == user_id]

    if status:
        jobs = [j for j in jobs if j.status == status]

    # Sort by created_at descending
    jobs.sort(key=lambda x: x.created_at, reverse=True)

    return jobs[offset : offset + limit]


@router.post("/webhook")
async def training_webhook(payload: dict):
    """
    Webhook endpoint for Replicate training status updates.
    """
    logger.info("Received training webhook", payload=payload)

    job_id = payload.get("input", {}).get("job_id")
    if not job_id or job_id not in training_jobs:
        logger.warning("Unknown job in webhook", job_id=job_id)
        return {"status": "ignored"}

    job = training_jobs[job_id]
    status = payload.get("status")
    output = payload.get("output")

    if status == "succeeded":
        job.status = TrainingStatus.COMPLETED
        job.progress = 1.0
        job.model_url = output.get("model") if output else None
    elif status == "failed":
        job.status = TrainingStatus.FAILED
        job.error_message = payload.get("error", "Training failed")
    elif status == "processing":
        job.status = TrainingStatus.TRAINING
        # Update progress from logs if available
        logs = payload.get("logs", "")
        if "step" in logs.lower():
            try:
                # Parse progress from logs
                pass
            except:
                pass

    job.updated_at = datetime.utcnow()

    logger.info("Updated job from webhook", job_id=job_id, status=job.status)
    return {"status": "processed"}
