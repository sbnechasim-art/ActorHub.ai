"""Training background tasks."""

import structlog
import httpx
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .routes import TrainingRequest
    from .config import Settings

logger = structlog.get_logger()


async def start_training_job(
    job_id: str,
    request: "TrainingRequest",
    settings: "Settings",
):
    """
    Start the training job process.

    Steps:
    1. Download and validate images
    2. Preprocess images (crop faces, resize)
    3. Upload to S3
    4. Create Replicate training job
    5. Update job status
    """
    from .routes import training_jobs, TrainingStatus

    if job_id not in training_jobs:
        logger.error("Job not found", job_id=job_id)
        return

    job = training_jobs[job_id]

    try:
        # Step 1: Preprocessing
        job.status = TrainingStatus.PREPROCESSING
        job.progress = 0.1
        job.updated_at = datetime.utcnow()

        logger.info("Starting preprocessing", job_id=job_id)

        # Download and validate images
        valid_images = []
        async with httpx.AsyncClient() as client:
            for i, url in enumerate(request.image_urls):
                try:
                    response = await client.get(url, timeout=30.0)
                    if response.status_code == 200:
                        valid_images.append(response.content)
                        job.progress = 0.1 + (0.2 * (i + 1) / len(request.image_urls))
                        job.updated_at = datetime.utcnow()
                except Exception as e:
                    logger.warning("Failed to download image", url=url, error=str(e))

        if len(valid_images) < settings.min_images_per_pack:
            raise ValueError(f"Only {len(valid_images)} valid images, minimum required: {settings.min_images_per_pack}")

        logger.info("Preprocessing complete", job_id=job_id, num_images=len(valid_images))

        # Step 2: Start training
        job.status = TrainingStatus.TRAINING
        job.progress = 0.3
        job.updated_at = datetime.utcnow()

        logger.info("Starting Replicate training", job_id=job_id)

        # Create Replicate training job
        if settings.replicate_api_token:
            async with httpx.AsyncClient() as client:
                # This is a simplified version - actual implementation would use Replicate SDK
                training_response = await client.post(
                    "https://api.replicate.com/v1/trainings",
                    headers={
                        "Authorization": f"Token {settings.replicate_api_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.replicate_model_version,
                        "input": {
                            "job_id": job_id,
                            "trigger_word": request.trigger_word,
                            "steps": request.training_steps,
                            "learning_rate": request.learning_rate,
                        },
                        "webhook": f"{settings.webhook_callback_url}/api/v1/webhook",
                    },
                    timeout=60.0,
                )

                if training_response.status_code not in [200, 201]:
                    raise ValueError(f"Replicate API error: {training_response.text}")

                replicate_job = training_response.json()
                logger.info("Replicate job created", replicate_id=replicate_job.get("id"))

        # Simulate training progress (in production, this comes from webhooks)
        import asyncio
        for i in range(10):
            await asyncio.sleep(2)  # Simulated delay
            job.progress = 0.3 + (0.6 * (i + 1) / 10)
            job.updated_at = datetime.utcnow()

        # Step 3: Complete
        job.status = TrainingStatus.COMPLETED
        job.progress = 1.0
        job.model_url = f"s3://{settings.s3_bucket_models}/{job_id}/model.safetensors"
        job.updated_at = datetime.utcnow()

        logger.info("Training completed", job_id=job_id, model_url=job.model_url)

        # Send webhook if configured
        if request.webhook_url:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        request.webhook_url,
                        json={
                            "event": "training.completed",
                            "job_id": job_id,
                            "actor_pack_id": request.actor_pack_id,
                            "model_url": job.model_url,
                        },
                        timeout=10.0,
                    )
            except Exception as e:
                logger.warning("Failed to send webhook", error=str(e))

    except Exception as e:
        logger.error("Training failed", job_id=job_id, error=str(e))
        job.status = TrainingStatus.FAILED
        job.error_message = str(e)
        job.updated_at = datetime.utcnow()

        # Send failure webhook
        if request.webhook_url:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        request.webhook_url,
                        json={
                            "event": "training.failed",
                            "job_id": job_id,
                            "actor_pack_id": request.actor_pack_id,
                            "error": str(e),
                        },
                        timeout=10.0,
                    )
            except:
                pass


async def cancel_training_job(job_id: str):
    """Cancel a training job on Replicate."""
    logger.info("Cancelling training job", job_id=job_id)

    # In production, would call Replicate API to cancel
    # await replicate.cancel(replicate_job_id)
