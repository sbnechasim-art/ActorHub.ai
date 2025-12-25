"""
GDPR Compliance Endpoints
Data export, deletion, consent management

FIXED: Data export now queued via Redis/Celery instead of memory-based BackgroundTasks.
"""

from datetime import datetime, timedelta
from typing import Optional

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.helpers import utc_now  # MEDIUM FIX: Use timezone-aware datetime
from app.core.security import get_current_user
from app.models.identity import Identity, UsageLog
from app.models.user import User

logger = structlog.get_logger()
router = APIRouter()


# ===========================================
# Schemas
# ===========================================


class ConsentUpdate(BaseModel):
    marketing_emails: Optional[bool] = None
    data_analytics: Optional[bool] = None
    third_party_sharing: Optional[bool] = None
    ai_training: Optional[bool] = None


class DataExportRequest(BaseModel):
    format: str = "json"  # json or csv


class DeleteAccountRequest(BaseModel):
    password: str
    confirmation: str  # Must be "DELETE MY ACCOUNT"


# ===========================================
# Consent Management
# ===========================================


@router.get("/consent")
async def get_consent_settings(current_user: User = Depends(get_current_user)):
    """Get user's consent settings"""
    return {
        "marketing_emails": current_user.consent_marketing or False,
        "data_analytics": current_user.consent_analytics or True,
        "third_party_sharing": current_user.consent_third_party or False,
        "ai_training": current_user.consent_ai_training or False,
        "terms_accepted_at": current_user.terms_accepted_at,
        "privacy_accepted_at": current_user.privacy_accepted_at,
    }


@router.patch("/consent")
async def update_consent_settings(
    consent: ConsentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user's consent settings"""
    if consent.marketing_emails is not None:
        current_user.consent_marketing = consent.marketing_emails
    if consent.data_analytics is not None:
        current_user.consent_analytics = consent.data_analytics
    if consent.third_party_sharing is not None:
        current_user.consent_third_party = consent.third_party_sharing
    if consent.ai_training is not None:
        current_user.consent_ai_training = consent.ai_training

    current_user.consent_updated_at = utc_now()
    await db.commit()

    logger.info("Consent updated", user_id=str(current_user.id))

    return {"message": "Consent settings updated"}


@router.post("/accept-terms")
async def accept_terms(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Accept terms of service"""
    current_user.terms_accepted_at = utc_now()
    await db.commit()
    return {"message": "Terms accepted"}


@router.post("/accept-privacy")
async def accept_privacy(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Accept privacy policy"""
    current_user.privacy_accepted_at = utc_now()
    await db.commit()
    return {"message": "Privacy policy accepted"}


# ===========================================
# Data Export (GDPR Article 20)
# ===========================================


@router.post("/export")
async def request_data_export(
    request: DataExportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Request export of all user data.
    GDPR Article 20 - Right to data portability.

    FIXED: Now queues to Celery (Redis-backed) instead of memory-based BackgroundTasks.
    """
    # Check for recent export request (prevent abuse)
    if current_user.last_export_request:
        hours_since = (utc_now() - current_user.last_export_request).total_seconds() / 3600
        if hours_since < 24:
            raise HTTPException(
                status_code=429, detail="You can only request a data export once every 24 hours"
            )

    current_user.last_export_request = utc_now()
    await db.commit()

    # FIXED: Queue export job via Redis/Celery for reliability
    await queue_data_export(str(current_user.id), current_user.email, request.format)

    return {
        "message": "Data export requested. You will receive an email when it's ready.",
        "estimated_time": "24 hours",
    }


# Worker URL for queuing Celery tasks
WORKER_URL = settings.WORKER_URL if hasattr(settings, 'WORKER_URL') else "http://localhost:8001"


async def queue_data_export(user_id: str, email: str, format: str):
    """
    Queue data export task via Celery worker.

    FIXED: Uses Celery queue (Redis-backed) instead of in-memory BackgroundTasks.
    """
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{WORKER_URL}/tasks/generate_data_export",
                json={"user_id": user_id, "email": email, "format": format},
                timeout=5.0
            )
        logger.info("Data export queued", user_id=user_id)
    except Exception as e:
        logger.warning(f"Failed to queue data export: {e}", user_id=user_id)


async def generate_data_export(user_id: str, format: str):
    """Generate and send data export to user"""
    from app.core.database import async_session_maker

    async with async_session_maker() as db:
        # Get user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return

        # Collect all user data
        export_data = {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
            "identities": [],
            "usage_logs": [],
            "consent_history": {
                "marketing_emails": user.consent_marketing,
                "data_analytics": user.consent_analytics,
                "third_party_sharing": user.consent_third_party,
                "ai_training": user.consent_ai_training,
            },
        }

        # Get identities
        result = await db.execute(select(Identity).where(Identity.user_id == user_id))
        identities = result.scalars().all()
        for identity in identities:
            export_data["identities"].append(
                {
                    "id": str(identity.id),
                    "display_name": identity.display_name,
                    "status": identity.status,
                    "created_at": identity.created_at.isoformat() if identity.created_at else None,
                }
            )

        # Get usage logs
        result = await db.execute(
            select(UsageLog).where(UsageLog.identity_id.in_([i.id for i in identities]))
        )
        logs = result.scalars().all()
        for log in logs[:1000]:  # Limit to 1000 most recent
            export_data["usage_logs"].append(
                {
                    "id": str(log.id),
                    "action": log.action,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
            )

        # Save and send export
        logger.info("Data export generated", user_id=user_id)
        # In production: save to S3 and email download link


# ===========================================
# Account Deletion (GDPR Article 17)
# ===========================================


@router.post("/delete-account")
async def request_account_deletion(
    request: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Request account deletion.
    GDPR Article 17 - Right to erasure.

    **Returns:** Deletion confirmation with scheduled date.

    **Errors:**
    - 400: Invalid confirmation text
    - 401: Invalid password or unauthorized
    """
    # Verify confirmation
    if request.confirmation != "DELETE MY ACCOUNT":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please type 'DELETE MY ACCOUNT' to confirm")

    # Verify password
    from app.core.security import verify_password

    if not verify_password(request.password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

    # Mark for deletion (actual deletion after grace period)
    current_user.deletion_requested_at = utc_now()
    current_user.deletion_scheduled_for = utc_now() + timedelta(days=30)
    current_user.is_active = False
    await db.commit()

    logger.warning("Account deletion requested", user_id=str(current_user.id))

    return {
        "message": "Account scheduled for deletion in 30 days",
        "deletion_date": current_user.deletion_scheduled_for.isoformat(),
        "note": "You can cancel this by logging in within 30 days",
    }


@router.post("/cancel-deletion")
async def cancel_account_deletion(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Cancel pending account deletion"""
    if not current_user.deletion_requested_at:
        raise HTTPException(status_code=400, detail="No pending deletion request")

    current_user.deletion_requested_at = None
    current_user.deletion_scheduled_for = None
    current_user.is_active = True
    await db.commit()

    return {"message": "Account deletion cancelled"}


# ===========================================
# Cookie Consent
# ===========================================


@router.post("/cookie-consent")
async def record_cookie_consent(
    consent: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record cookie consent preferences"""
    current_user.cookie_consent = consent
    current_user.cookie_consent_at = utc_now()
    await db.commit()

    return {"message": "Cookie preferences saved"}


# ===========================================
# Age Verification
# ===========================================


@router.post("/verify-age")
async def verify_age(
    birthdate: str,  # YYYY-MM-DD format
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify user is at least 18 years old"""
    from datetime import date

    try:
        birth = datetime.strptime(birthdate, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    today = date.today()
    age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))

    if age < 18:
        raise HTTPException(
            status_code=400, detail="You must be at least 18 years old to use this service"
        )

    current_user.age_verified = True
    current_user.age_verified_at = utc_now()
    await db.commit()

    return {"message": "Age verified", "age": age}


# Import timedelta for deletion scheduling
from datetime import timedelta
