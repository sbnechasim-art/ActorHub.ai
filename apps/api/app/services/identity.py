"""
Identity Service
Business logic for identity registration and verification

Encapsulates:
- Identity registration workflow
- Face verification
- Gallery management
- Usage statistics
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import numpy as np
import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.helpers import utc_now  # MEDIUM FIX: Use timezone-aware datetime
from app.models.identity import Identity, IdentityStatus, UsageLog
from app.models.user import User, ApiKey
from app.services.face_recognition import FaceRecognitionService
from app.services.storage import StorageService

logger = structlog.get_logger()

# Allowed image MIME types (magic bytes)
ALLOWED_IMAGE_HEADERS = {
    b'\xff\xd8\xff': 'image/jpeg',
    b'\x89PNG': 'image/png',
    b'GIF87a': 'image/gif',
    b'GIF89a': 'image/gif',
    b'RIFF': 'image/webp',
}


class IdentityService:
    """Service for identity-related operations"""

    def __init__(
        self,
        db: AsyncSession,
        face_service: Optional[FaceRecognitionService] = None,
        storage_service: Optional[StorageService] = None,
    ):
        self.db = db
        self.face_service = face_service or FaceRecognitionService()
        self.storage_service = storage_service or StorageService()

    # ===========================================
    # Image Validation
    # ===========================================

    def validate_image_format(self, image_bytes: bytes) -> Optional[str]:
        """
        Validate image format by checking magic bytes.

        Returns:
            MIME type if valid, None if invalid
        """
        for header, mime in ALLOWED_IMAGE_HEADERS.items():
            if image_bytes[:len(header)] == header:
                return mime

        # Special check for WebP (RIFF + WEBP)
        if image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
            return 'image/webp'

        return None

    def validate_image_size(self, image_bytes: bytes, max_mb: int = 10) -> bool:
        """Check if image is within size limit"""
        return len(image_bytes) <= max_mb * 1024 * 1024

    # ===========================================
    # Identity Registration
    # ===========================================

    async def register_identity(
        self,
        user: User,
        display_name: str,
        face_bytes: bytes,
        verification_bytes: bytes,
        protection_level: str = "FREE",
        allow_commercial: bool = False,
        allow_ai_training: bool = False,
        show_in_public_gallery: bool = False,
    ) -> Identity:
        """
        Register a new protected identity.

        Args:
            user: Owner of the identity
            display_name: Display name for the identity
            face_bytes: Primary face photo bytes
            verification_bytes: Verification selfie bytes
            protection_level: FREE, PRO, or ENTERPRISE
            allow_commercial: Allow commercial use
            allow_ai_training: Allow AI training
            show_in_public_gallery: Show in public gallery

        Returns:
            Created Identity object

        Raises:
            ValueError: If validation fails
        """
        # Validate image formats
        face_mime = self.validate_image_format(face_bytes)
        if not face_mime:
            raise ValueError("Invalid face image format. Supported: JPEG, PNG, GIF, WebP")

        verification_mime = self.validate_image_format(verification_bytes)
        if not verification_mime:
            raise ValueError("Invalid verification image format. Supported: JPEG, PNG, GIF, WebP")

        # Validate sizes
        if not self.validate_image_size(face_bytes):
            raise ValueError("Face image too large (max 10MB)")
        if not self.validate_image_size(verification_bytes):
            raise ValueError("Verification image too large (max 10MB)")

        # Extract face embeddings
        embedding = await self.face_service.extract_embedding(face_bytes)
        if embedding is None:
            raise ValueError("Could not detect face in image. Please use a clear, front-facing photo.")

        # Liveness check
        is_live = await self.face_service.liveness_check(verification_bytes)
        if not is_live:
            raise ValueError("Liveness check failed. Please take a new selfie with good lighting.")

        # Verify same person in both images
        verification_embedding = await self.face_service.extract_embedding(verification_bytes)
        if verification_embedding is None:
            raise ValueError("Could not detect face in verification selfie.")

        face_similarity = float(np.dot(embedding, verification_embedding))
        logger.info(f"Face verification similarity score: {face_similarity:.3f}")

        if face_similarity < settings.FACE_SIMILARITY_THRESHOLD:
            raise ValueError(
                "Face verification failed. The face in your photo does not match your verification selfie."
            )

        # Check for duplicates
        similar = await self.face_service.find_similar(
            embedding, threshold=settings.FACE_DUPLICATE_THRESHOLD
        )
        if similar:
            raise ValueError("This face is already registered. If this is your face, please contact support.")

        # Upload face image to storage
        file_uuid = uuid.uuid4()
        face_filename = f"identities/{user.id}/{file_uuid}_face.jpg"
        face_image_url = await self.storage_service.upload_file(
            file_bytes=face_bytes,
            filename=face_filename,
            content_type="image/jpeg",
        )

        # Create identity record
        identity = Identity(
            user_id=user.id,
            display_name=display_name,
            profile_image_url=face_image_url,
            status="VERIFIED",
            protection_level=protection_level.upper(),
            allow_commercial_use=allow_commercial,
            allow_ai_training=allow_ai_training,
            show_in_public_gallery=show_in_public_gallery,
            verified_at=utc_now(),
            verification_method="selfie",
            verification_data={
                "face_similarity_score": round(face_similarity, 4),
                "similarity_threshold": settings.FACE_SIMILARITY_THRESHOLD,
                "verification_passed": True,
            },
        )
        self.db.add(identity)
        await self.db.commit()
        await self.db.refresh(identity)

        # Store embedding in vector database
        await self.face_service.register_embedding(identity.id, embedding)

        logger.info(
            "Identity registered",
            identity_id=str(identity.id),
            user_id=str(user.id),
        )

        return identity

    # ===========================================
    # Face Verification
    # ===========================================

    async def verify_faces(
        self,
        image_bytes: Optional[bytes] = None,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        api_key: Optional[ApiKey] = None,
        include_license_options: bool = False,
    ) -> Dict[str, Any]:
        """
        Verify faces in an image against registered identities.

        Returns:
            Verification results with matched identities
        """
        import time
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Detect faces
        faces = []
        if image_base64:
            faces = await self.face_service.detect_faces_base64(image_base64)
        elif image_url:
            faces = await self.face_service.detect_faces_url(image_url)
        elif image_bytes:
            # Convert bytes to base64 and use existing method
            import base64
            image_base64_str = base64.b64encode(image_bytes).decode('utf-8')
            faces = await self.face_service.detect_faces_base64(image_base64_str)

        response_time_ms = int((time.time() - start_time) * 1000)

        if not faces:
            return {
                "protected": False,
                "faces_detected": 0,
                "identities": [],
                "message": "No faces detected in image",
                "response_time_ms": response_time_ms,
                "request_id": request_id,
            }

        # Check each face
        results = []
        any_protected = False

        for face in faces:
            embedding = face["embedding"]
            match = await self.face_service.find_match(
                embedding, threshold=settings.FACE_SIMILARITY_THRESHOLD
            )

            if match:
                any_protected = True
                identity = await self.db.get(Identity, UUID(match["identity_id"]))

                if identity:
                    # Log verification
                    if api_key:
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
                        self.db.add(usage_log)
                        identity.total_verifications += 1

                    # Build result
                    result = {
                        "protected": True,
                        "identity_id": str(identity.id),
                        "display_name": identity.display_name,
                        "similarity_score": match["score"],
                        "allow_commercial": identity.allow_commercial_use,
                        "blocked_categories": identity.blocked_categories or [],
                        "license_required": identity.allow_commercial_use,
                        "face_bbox": face.get("bbox"),
                    }

                    if include_license_options and identity.allow_commercial_use:
                        result["license_options"] = self._build_license_options(identity)

                    results.append(result)
                else:
                    results.append({
                        "protected": True,
                        "identity_id": match["identity_id"],
                        "similarity_score": match["score"],
                        "license_required": True,
                        "face_bbox": face.get("bbox"),
                    })
            else:
                results.append({"protected": False, "face_bbox": face.get("bbox")})

        await self.db.commit()

        return {
            "protected": any_protected,
            "faces_detected": len(faces),
            "identities": results,
            "message": "Protected identity detected" if any_protected else "No protected identities found",
            "response_time_ms": int((time.time() - start_time) * 1000),
            "request_id": request_id,
        }

    def _build_license_options(self, identity: Identity) -> List[Dict[str, Any]]:
        """Build license options for an identity"""
        base_price = identity.base_license_fee or 99
        return [
            {
                "type": "single_use",
                "price_usd": base_price,
                "includes": "Single commercial use",
            },
            {
                "type": "subscription",
                "price_usd": base_price * 3,
                "duration_days": 30,
                "includes": "Unlimited use for 30 days",
            },
        ]

    # ===========================================
    # Gallery
    # ===========================================

    async def get_public_gallery(
        self,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Identity]:
        """Get verified identities that opted into public gallery"""
        query = (
            select(Identity)
            .where(
                Identity.show_in_public_gallery == True,
                Identity.status == "VERIFIED",
                Identity.deleted_at.is_(None),
            )
            .order_by(Identity.verified_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ===========================================
    # Statistics
    # ===========================================

    async def get_identity_stats(
        self,
        identity_id: UUID,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get usage statistics for an identity"""
        identity = await self.db.get(Identity, identity_id)
        if not identity:
            raise ValueError("Identity not found")

        since = utc_now() - timedelta(days=days)

        # Count verifications
        verifications_count = await self.db.scalar(
            select(func.count(UsageLog.id)).where(
                UsageLog.identity_id == identity_id,
                UsageLog.action == "verify",
                UsageLog.created_at >= since,
            )
        ) or 0

        # Count matches
        matches_count = await self.db.scalar(
            select(func.count(UsageLog.id)).where(
                UsageLog.identity_id == identity_id,
                UsageLog.action == "verify",
                UsageLog.matched.is_(True),
                UsageLog.created_at >= since,
            )
        ) or 0

        return {
            "identity_id": str(identity_id),
            "period_days": days,
            "total_verifications": verifications_count,
            "total_matches": matches_count,
            "total_licenses": identity.total_licenses,
            "total_revenue_usd": identity.total_revenue,
            "protection_level": identity.protection_level,
        }

    # ===========================================
    # CRUD Operations
    # ===========================================

    async def get_user_identities(
        self,
        user: User,
        status: Optional[str] = None,
    ) -> List[Identity]:
        """Get all identities owned by a user"""
        query = select(Identity).where(
            Identity.user_id == user.id,
            Identity.deleted_at.is_(None),
        )

        if status:
            query = query.where(Identity.status == status)

        query = query.order_by(Identity.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_identity(self, identity_id: UUID) -> Optional[Identity]:
        """Get an identity by ID"""
        identity = await self.db.get(Identity, identity_id)
        if identity and identity.deleted_at:
            return None
        return identity

    async def update_identity(
        self,
        identity: Identity,
        updates: Dict[str, Any],
        allowed_fields: set,
    ) -> Identity:
        """Update identity with validated fields"""
        for field, value in updates.items():
            if field not in allowed_fields:
                raise ValueError(f"Field '{field}' cannot be modified")
            setattr(identity, field, value)

        identity.updated_at = utc_now()
        await self.db.commit()
        await self.db.refresh(identity)

        return identity

    async def delete_identity(self, identity: Identity) -> None:
        """Soft delete an identity"""
        identity.deleted_at = utc_now()
        identity.status = "SUSPENDED"

        # Remove from vector database
        await self.face_service.delete_embedding(identity.id)

        await self.db.commit()

        logger.info("Identity deleted", identity_id=str(identity.id))


# ===========================================
# Dependency for FastAPI
# ===========================================

async def get_identity_service(db: AsyncSession) -> IdentityService:
    """FastAPI dependency for IdentityService"""
    return IdentityService(db)
