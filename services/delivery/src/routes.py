"""Delivery Service API Routes."""

import structlog
import hashlib
import io
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query, Response
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

import boto3
from botocore.exceptions import ClientError

from .config import get_settings, Settings

router = APIRouter(tags=["delivery"])
logger = structlog.get_logger()


class ContentType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    MODEL = "model"
    THUMBNAIL = "thumbnail"


class SignedUrlRequest(BaseModel):
    """Request for a signed download URL."""
    content_id: str = Field(..., description="Content ID")
    content_type: ContentType = Field(default=ContentType.IMAGE)
    size: Optional[int] = Field(None, description="Thumbnail size (128, 256, 512)")


class SignedUrlResponse(BaseModel):
    """Signed URL response."""
    url: str
    expires_at: datetime
    content_type: str
    size: Optional[int] = None


class UploadRequest(BaseModel):
    """Request for a presigned upload URL."""
    filename: str
    content_type: str
    size_bytes: int
    actor_pack_id: Optional[str] = None


class UploadUrlResponse(BaseModel):
    """Presigned upload URL response."""
    upload_url: str
    content_id: str
    fields: dict
    expires_at: datetime


def get_settings_dep() -> Settings:
    return get_settings()


def get_s3_client(settings: Settings):
    """Get S3 client."""
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
    )


@router.post("/download/signed-url", response_model=SignedUrlResponse)
async def get_signed_download_url(
    request: SignedUrlRequest,
    settings: Settings = Depends(get_settings_dep),
):
    """
    Get a signed URL for downloading content.

    This provides time-limited access to protected content.
    """
    logger.info("Generating signed download URL", content_id=request.content_id)

    # Determine bucket and key
    bucket = settings.s3_bucket_content
    if request.content_type == ContentType.MODEL:
        bucket = settings.s3_bucket_generated

    key = f"{request.content_type.value}/{request.content_id}"
    if request.size and request.content_type == ContentType.THUMBNAIL:
        key = f"thumbnails/{request.size}/{request.content_id}"

    try:
        s3_client = get_s3_client(settings)

        # Generate presigned URL
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=settings.signed_url_expiry_seconds,
        )

        expires_at = datetime.utcnow() + timedelta(seconds=settings.signed_url_expiry_seconds)

        return SignedUrlResponse(
            url=url,
            expires_at=expires_at,
            content_type=request.content_type.value,
            size=request.size,
        )

    except ClientError as e:
        logger.error("S3 error generating signed URL", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate download URL")


@router.post("/upload/presigned", response_model=UploadUrlResponse)
async def get_presigned_upload_url(
    request: UploadRequest,
    settings: Settings = Depends(get_settings_dep),
):
    """
    Get a presigned URL for uploading content directly to S3.

    This allows clients to upload large files directly to storage.
    """
    logger.info("Generating presigned upload URL", filename=request.filename)

    # Generate content ID
    content_id = hashlib.sha256(
        f"{request.filename}{datetime.utcnow().isoformat()}".encode()
    ).hexdigest()[:16]

    # Determine key
    key = f"uploads/{content_id}/{request.filename}"
    if request.actor_pack_id:
        key = f"actor-packs/{request.actor_pack_id}/{content_id}/{request.filename}"

    try:
        s3_client = get_s3_client(settings)

        # Generate presigned POST
        presigned = s3_client.generate_presigned_post(
            Bucket=settings.s3_bucket_content,
            Key=key,
            Fields={
                "Content-Type": request.content_type,
            },
            Conditions=[
                {"Content-Type": request.content_type},
                ["content-length-range", 1, request.size_bytes],
            ],
            ExpiresIn=3600,  # 1 hour
        )

        expires_at = datetime.utcnow() + timedelta(hours=1)

        return UploadUrlResponse(
            upload_url=presigned["url"],
            content_id=content_id,
            fields=presigned["fields"],
            expires_at=expires_at,
        )

    except ClientError as e:
        logger.error("S3 error generating upload URL", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate upload URL")


@router.get("/content/{content_id}")
async def get_content(
    content_id: str,
    content_type: ContentType = Query(default=ContentType.IMAGE),
    redirect: bool = Query(default=True, description="Redirect to signed URL"),
    settings: Settings = Depends(get_settings_dep),
):
    """
    Get content by ID.

    Can either redirect to a signed URL or stream the content directly.
    """
    logger.info("Getting content", content_id=content_id, content_type=content_type)

    bucket = settings.s3_bucket_content
    key = f"{content_type.value}/{content_id}"

    try:
        s3_client = get_s3_client(settings)

        if redirect:
            # Generate signed URL and redirect
            url = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=settings.signed_url_expiry_seconds,
            )
            return RedirectResponse(url=url, status_code=302)
        else:
            # Stream content directly
            response = s3_client.get_object(Bucket=bucket, Key=key)
            content = response["Body"].read()
            content_type_header = response.get("ContentType", "application/octet-stream")

            return Response(
                content=content,
                media_type=content_type_header,
                headers={
                    "Cache-Control": "private, max-age=3600",
                    "Content-Disposition": f'inline; filename="{content_id}"',
                },
            )

    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            raise HTTPException(status_code=404, detail="Content not found")
        logger.error("S3 error getting content", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve content")


@router.get("/thumbnail/{content_id}")
async def get_thumbnail(
    content_id: str,
    size: int = Query(default=256, description="Thumbnail size"),
    settings: Settings = Depends(get_settings_dep),
):
    """Get thumbnail for content."""
    if size not in settings.thumbnail_sizes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid size. Allowed sizes: {settings.thumbnail_sizes}",
        )

    logger.info("Getting thumbnail", content_id=content_id, size=size)

    bucket = settings.s3_bucket_content
    key = f"thumbnails/{size}/{content_id}"

    try:
        s3_client = get_s3_client(settings)

        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=settings.signed_url_expiry_seconds,
        )

        return RedirectResponse(url=url, status_code=302)

    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            # Generate thumbnail on-the-fly (placeholder - implement actual generation)
            raise HTTPException(status_code=404, detail="Thumbnail not found")
        raise HTTPException(status_code=500, detail="Failed to retrieve thumbnail")


@router.delete("/content/{content_id}")
async def delete_content(
    content_id: str,
    content_type: ContentType = Query(default=ContentType.IMAGE),
    settings: Settings = Depends(get_settings_dep),
):
    """Delete content by ID."""
    logger.info("Deleting content", content_id=content_id)

    bucket = settings.s3_bucket_content
    key = f"{content_type.value}/{content_id}"

    try:
        s3_client = get_s3_client(settings)
        s3_client.delete_object(Bucket=bucket, Key=key)

        # Also delete thumbnails
        for size in settings.thumbnail_sizes:
            try:
                s3_client.delete_object(
                    Bucket=bucket,
                    Key=f"thumbnails/{size}/{content_id}",
                )
            except:
                pass

        logger.info("Content deleted", content_id=content_id)
        return {"deleted": True, "content_id": content_id}

    except ClientError as e:
        logger.error("S3 error deleting content", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete content")


@router.get("/batch/signed-urls")
async def get_batch_signed_urls(
    content_ids: str = Query(..., description="Comma-separated content IDs"),
    content_type: ContentType = Query(default=ContentType.IMAGE),
    settings: Settings = Depends(get_settings_dep),
):
    """Get signed URLs for multiple content items."""
    ids = [id.strip() for id in content_ids.split(",") if id.strip()]

    if len(ids) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 items per batch")

    logger.info("Generating batch signed URLs", count=len(ids))

    s3_client = get_s3_client(settings)
    bucket = settings.s3_bucket_content

    results = {}
    for content_id in ids:
        key = f"{content_type.value}/{content_id}"
        try:
            url = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=settings.signed_url_expiry_seconds,
            )
            results[content_id] = {
                "url": url,
                "expires_at": (
                    datetime.utcnow() + timedelta(seconds=settings.signed_url_expiry_seconds)
                ).isoformat(),
            }
        except ClientError:
            results[content_id] = {"error": "Failed to generate URL"}

    return {"urls": results, "count": len(results)}
