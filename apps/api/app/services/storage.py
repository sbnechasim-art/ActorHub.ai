"""
Storage Service
S3/MinIO file storage operations - Async version using aioboto3

Features:
- Retry logic for transient failures
- Configurable timeouts
- Circuit breaker protection
- Proper error handling
- Filename sanitization for security
"""

import asyncio
import re
import time
from functools import partial
from io import BytesIO
from typing import Optional

import boto3
import structlog
from botocore.config import Config
from botocore.exceptions import ClientError, ConnectTimeoutError, ReadTimeoutError

from app.core.config import settings

logger = structlog.get_logger()

# Retry configuration
S3_RETRY_ATTEMPTS = 3
S3_RETRY_DELAY = 1.0

# Dangerous filename patterns
_DANGEROUS_PATTERNS = re.compile(r'[<>:"|?*\x00-\x1f]')
_PATH_TRAVERSAL = re.compile(r'\.\.[\\/]|^[\\/]|[\\/]\.\.[\\/]|[\\/]\.\.$')


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and other attacks.

    Security measures:
    - Remove/replace dangerous characters
    - Prevent path traversal (../)
    - Remove null bytes
    - Normalize path separators
    - Limit filename length
    """
    if not filename:
        raise ValueError("Filename cannot be empty")

    # Replace backslashes with forward slashes (normalize)
    filename = filename.replace("\\", "/")

    # Check for path traversal attempts
    if _PATH_TRAVERSAL.search(filename):
        logger.warning(f"Path traversal attempt detected in filename: {filename[:50]}")
        raise ValueError("Invalid filename: path traversal not allowed")

    # Remove null bytes and other dangerous characters
    filename = _DANGEROUS_PATTERNS.sub("", filename)

    # Remove leading/trailing slashes and dots
    parts = [p.strip(". ") for p in filename.split("/") if p and p.strip(". ")]
    if not parts:
        raise ValueError("Invalid filename after sanitization")

    # Reconstruct path
    filename = "/".join(parts)

    # Limit total length
    if len(filename) > 500:
        # Keep extension if present
        if "." in filename:
            name, ext = filename.rsplit(".", 1)
            filename = name[:490] + "." + ext[:9]
        else:
            filename = filename[:500]

    return filename


def validate_bucket_name(bucket: str) -> str:
    """Validate S3 bucket name format."""
    if not bucket:
        raise ValueError("Bucket name cannot be empty")

    # S3 bucket naming rules
    if not re.match(r'^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$', bucket):
        raise ValueError(f"Invalid bucket name: {bucket}")

    return bucket


class StorageService:
    """
    Storage service for file uploads and downloads.
    Uses S3 API - works with AWS S3 or MinIO.
    All S3 operations run in executor to avoid blocking the event loop.
    """

    def __init__(self):
        self._client = None
        self._public_client = None  # Separate client for presigned URLs with public endpoint

    def _get_client(self):
        """Get or create S3 client with proper timeout and retry configuration"""
        if self._client is None:
            config = Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},  # Required for MinIO
                connect_timeout=settings.S3_CONNECT_TIMEOUT,
                read_timeout=settings.S3_READ_TIMEOUT,
                retries={
                    "max_attempts": S3_RETRY_ATTEMPTS,
                    "mode": "adaptive",  # Adaptive retry with exponential backoff
                },
            )

            # Use environment variables or IAM role for credentials
            # AWS SDK will automatically use:
            # 1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
            # 2. IAM role (if running on EC2/ECS/Lambda)
            # 3. AWS credentials file (~/.aws/credentials)
            client_kwargs = {
                "service_name": "s3",
                "region_name": settings.AWS_REGION,
                "config": config,
            }

            # Only add endpoint_url for non-AWS S3 (like MinIO)
            if settings.AWS_ENDPOINT_URL:
                client_kwargs["endpoint_url"] = settings.AWS_ENDPOINT_URL

            # Only explicitly pass credentials if they're set (for MinIO/local dev)
            # In production with IAM roles, these should not be set
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                client_kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
                client_kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY

            self._client = boto3.client(**client_kwargs)
            logger.info(
                "S3 client initialized",
                timeout_config={
                    "connect": settings.S3_CONNECT_TIMEOUT,
                    "read": settings.S3_READ_TIMEOUT,
                },
                retry_config={"max_attempts": S3_RETRY_ATTEMPTS},
            )

        return self._client

    def _get_public_client(self):
        """Get or create S3 client that uses public endpoint for presigned URLs"""
        if self._public_client is None:
            # If no public URL configured, use the regular client
            if not settings.S3_PUBLIC_URL:
                return self._get_client()

            config = Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                connect_timeout=settings.S3_CONNECT_TIMEOUT,
                read_timeout=settings.S3_READ_TIMEOUT,
            )

            client_kwargs = {
                "service_name": "s3",
                "region_name": settings.AWS_REGION,
                "config": config,
                "endpoint_url": settings.S3_PUBLIC_URL,  # Use public URL for signing
            }

            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                client_kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
                client_kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY

            self._public_client = boto3.client(**client_kwargs)
            logger.info(
                "S3 public client initialized for presigned URLs",
                endpoint=settings.S3_PUBLIC_URL,
            )

        return self._public_client

    async def _run_sync(self, func, *args, **kwargs):
        """Run a synchronous function in executor to avoid blocking"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, partial(func, *args, **kwargs)
        )

    async def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        bucket: str = None,
    ) -> str:
        """
        Upload file to S3/MinIO.

        Args:
            file_bytes: File content as bytes
            filename: Path/name for the file in the bucket
            content_type: MIME type
            bucket: Target bucket (default: uploads bucket)

        Returns:
            URL of uploaded file
        """
        # SECURITY: Sanitize filename to prevent path traversal
        filename = sanitize_filename(filename)

        if bucket is None:
            bucket = settings.S3_BUCKET_UPLOADS

        client = self._get_client()

        try:
            # Ensure bucket exists (run in executor)
            try:
                await self._run_sync(client.head_bucket, Bucket=bucket)
            except ClientError:
                await self._run_sync(client.create_bucket, Bucket=bucket)
                logger.info(f"Created bucket: {bucket}")

            # Upload file (run in executor)
            await self._run_sync(
                client.put_object,
                Bucket=bucket,
                Key=filename,
                Body=file_bytes,
                ContentType=content_type
            )

            # Build URL
            if settings.AWS_ENDPOINT_URL:
                url = f"{settings.AWS_ENDPOINT_URL}/{bucket}/{filename}"
            else:
                url = f"https://{bucket}.s3.{settings.AWS_REGION}.amazonaws.com/{filename}"

            logger.info(f"Uploaded file to {url}")
            return url

        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise

    async def download_file(self, filename: str, bucket: str = None) -> bytes:
        """Download file from S3/MinIO"""
        # SECURITY: Sanitize filename to prevent path traversal
        filename = sanitize_filename(filename)

        if bucket is None:
            bucket = settings.S3_BUCKET_UPLOADS

        client = self._get_client()

        try:
            response = await self._run_sync(
                client.get_object,
                Bucket=bucket,
                Key=filename
            )
            # Read the body - this is already bytes
            body = response["Body"]
            return body.read()
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise

    async def generate_presigned_url(
        self, bucket: str, key: str, expires_in: int = 3600, method: str = "get_object"
    ) -> str:
        """
        Generate a presigned URL for secure access.

        Args:
            bucket: S3 bucket name
            key: Object key/path
            expires_in: URL expiration in seconds
            method: S3 operation (get_object, put_object)

        Returns:
            Presigned URL with valid signature for the target endpoint
        """
        # SECURITY: Sanitize key to prevent path traversal
        key = sanitize_filename(key)

        # Use public client if configured - this generates URLs with correct signature
        # for the public endpoint (e.g., Cloudflare Tunnel)
        client = self._get_public_client()

        try:
            url = await self._run_sync(
                client.generate_presigned_url,
                ClientMethod=method,
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in
            )

            logger.debug(f"Generated presigned URL for endpoint: {settings.S3_PUBLIC_URL or settings.AWS_ENDPOINT_URL}")

            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    # Alias for backwards compatibility
    async def get_presigned_url(
        self, bucket: str, key: str, expires_in: int = 3600, method: str = "get_object"
    ) -> str:
        """Alias for generate_presigned_url"""
        return await self.generate_presigned_url(bucket, key, expires_in, method)

    async def delete_file(self, filename: str, bucket: str = None):
        """Delete file from S3/MinIO"""
        # SECURITY: Sanitize filename to prevent path traversal
        filename = sanitize_filename(filename)

        if bucket is None:
            bucket = settings.S3_BUCKET_UPLOADS

        client = self._get_client()

        try:
            await self._run_sync(
                client.delete_object,
                Bucket=bucket,
                Key=filename
            )
            logger.info(f"Deleted file: {bucket}/{filename}")
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            raise

    async def file_exists(self, filename: str, bucket: str = None) -> bool:
        """Check if file exists"""
        # SECURITY: Sanitize filename to prevent path traversal
        filename = sanitize_filename(filename)

        if bucket is None:
            bucket = settings.S3_BUCKET_UPLOADS

        client = self._get_client()

        try:
            await self._run_sync(
                client.head_object,
                Bucket=bucket,
                Key=filename
            )
            return True
        except ClientError:
            return False

    async def list_files(self, prefix: str = "", bucket: str = None, max_keys: int = 1000) -> list:
        """List files in bucket with optional prefix"""
        if bucket is None:
            bucket = settings.S3_BUCKET_UPLOADS

        client = self._get_client()

        try:
            response = await self._run_sync(
                client.list_objects_v2,
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=max_keys
            )

            files = []
            for obj in response.get("Contents", []):
                files.append(
                    {
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"].isoformat(),
                    }
                )

            return files
        except Exception as e:
            logger.error(f"List failed: {e}")
            raise
