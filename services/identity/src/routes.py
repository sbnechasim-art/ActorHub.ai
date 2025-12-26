"""Identity Service API Routes."""

import structlog
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel, Field
from typing import Optional
import httpx

from .config import get_settings, Settings

router = APIRouter(tags=["identity"])
logger = structlog.get_logger()


class VerificationRequest(BaseModel):
    """Identity verification request."""
    user_id: str = Field(..., description="User ID to verify")
    reference_image_url: Optional[str] = Field(None, description="Reference image URL")


class VerificationResult(BaseModel):
    """Identity verification result."""
    verified: bool
    confidence: float
    liveness_score: float
    quality_score: float
    message: str


class FaceComparisonRequest(BaseModel):
    """Face comparison request."""
    image1_url: str
    image2_url: str


class FaceComparisonResult(BaseModel):
    """Face comparison result."""
    match: bool
    similarity: float
    threshold: float


class LivenessCheckResult(BaseModel):
    """Liveness check result."""
    is_live: bool
    confidence: float
    checks: dict


def get_settings_dep() -> Settings:
    """Dependency for settings."""
    return get_settings()


@router.post("/verify", response_model=VerificationResult)
async def verify_identity(
    selfie: UploadFile = File(..., description="Live selfie image"),
    reference: Optional[UploadFile] = File(None, description="Reference document image"),
    user_id: Optional[str] = None,
    settings: Settings = Depends(get_settings_dep),
):
    """
    Verify user identity through face recognition.

    Performs:
    1. Liveness detection on selfie
    2. Face quality assessment
    3. Face comparison with reference (if provided)
    """
    logger.info("Starting identity verification", user_id=user_id)

    try:
        # Read selfie image
        selfie_data = await selfie.read()

        async with httpx.AsyncClient() as client:
            # 1. Liveness check
            liveness_response = await client.post(
                f"{settings.ml_service_url}/api/v1/liveness",
                files={"image": ("selfie.jpg", selfie_data, "image/jpeg")},
                timeout=30.0,
            )

            if liveness_response.status_code != 200:
                raise HTTPException(status_code=502, detail="Liveness check failed")

            liveness_result = liveness_response.json()
            liveness_score = liveness_result.get("confidence", 0)

            if liveness_score < settings.liveness_threshold:
                return VerificationResult(
                    verified=False,
                    confidence=0,
                    liveness_score=liveness_score,
                    quality_score=0,
                    message="Liveness check failed - please use a live camera",
                )

            # 2. Quality check
            quality_response = await client.post(
                f"{settings.ml_service_url}/api/v1/quality",
                files={"image": ("selfie.jpg", selfie_data, "image/jpeg")},
                timeout=30.0,
            )

            if quality_response.status_code != 200:
                raise HTTPException(status_code=502, detail="Quality check failed")

            quality_result = quality_response.json()
            quality_score = quality_result.get("overall", 0)

            if quality_score < settings.min_face_quality:
                return VerificationResult(
                    verified=False,
                    confidence=0,
                    liveness_score=liveness_score,
                    quality_score=quality_score,
                    message="Image quality too low - please ensure good lighting",
                )

            # 3. Face comparison (if reference provided)
            if reference:
                reference_data = await reference.read()

                compare_response = await client.post(
                    f"{settings.ml_service_url}/api/v1/compare",
                    files={
                        "image1": ("selfie.jpg", selfie_data, "image/jpeg"),
                        "image2": ("reference.jpg", reference_data, "image/jpeg"),
                    },
                    timeout=30.0,
                )

                if compare_response.status_code != 200:
                    raise HTTPException(status_code=502, detail="Face comparison failed")

                compare_result = compare_response.json()
                similarity = compare_result.get("similarity", 0)

                verified = similarity >= settings.similarity_threshold

                return VerificationResult(
                    verified=verified,
                    confidence=similarity,
                    liveness_score=liveness_score,
                    quality_score=quality_score,
                    message="Identity verified" if verified else "Face does not match reference",
                )

            # No reference - just return liveness and quality results
            return VerificationResult(
                verified=True,
                confidence=liveness_score,
                liveness_score=liveness_score,
                quality_score=quality_score,
                message="Liveness and quality verified",
            )

    except httpx.RequestError as e:
        logger.error("ML service connection error", error=str(e))
        raise HTTPException(status_code=503, detail="ML service unavailable")
    except Exception as e:
        logger.error("Verification error", error=str(e))
        raise HTTPException(status_code=500, detail="Verification failed")


@router.post("/compare", response_model=FaceComparisonResult)
async def compare_faces(
    image1: UploadFile = File(..., description="First face image"),
    image2: UploadFile = File(..., description="Second face image"),
    settings: Settings = Depends(get_settings_dep),
):
    """Compare two face images and return similarity score."""
    logger.info("Starting face comparison")

    try:
        image1_data = await image1.read()
        image2_data = await image2.read()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.ml_service_url}/api/v1/compare",
                files={
                    "image1": ("image1.jpg", image1_data, "image/jpeg"),
                    "image2": ("image2.jpg", image2_data, "image/jpeg"),
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                raise HTTPException(status_code=502, detail="Face comparison failed")

            result = response.json()
            similarity = result.get("similarity", 0)

            return FaceComparisonResult(
                match=similarity >= settings.similarity_threshold,
                similarity=similarity,
                threshold=settings.similarity_threshold,
            )

    except httpx.RequestError as e:
        logger.error("ML service connection error", error=str(e))
        raise HTTPException(status_code=503, detail="ML service unavailable")


@router.post("/liveness", response_model=LivenessCheckResult)
async def check_liveness(
    image: UploadFile = File(..., description="Face image to check"),
    settings: Settings = Depends(get_settings_dep),
):
    """Perform liveness detection on a face image."""
    logger.info("Starting liveness check")

    try:
        image_data = await image.read()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.ml_service_url}/api/v1/liveness",
                files={"image": ("image.jpg", image_data, "image/jpeg")},
                timeout=30.0,
            )

            if response.status_code != 200:
                raise HTTPException(status_code=502, detail="Liveness check failed")

            result = response.json()

            return LivenessCheckResult(
                is_live=result.get("is_live", False),
                confidence=result.get("confidence", 0),
                checks=result.get("checks", {}),
            )

    except httpx.RequestError as e:
        logger.error("ML service connection error", error=str(e))
        raise HTTPException(status_code=503, detail="ML service unavailable")


@router.get("/embedding/{user_id}")
async def get_user_embedding(
    user_id: str,
    settings: Settings = Depends(get_settings_dep),
):
    """Get stored face embedding for a user."""
    # This would typically fetch from a database or vector store
    logger.info("Fetching user embedding", user_id=user_id)

    # Placeholder - implement actual storage retrieval
    raise HTTPException(status_code=404, detail="User embedding not found")
