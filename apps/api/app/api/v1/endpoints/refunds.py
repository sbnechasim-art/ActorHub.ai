"""
Refund Endpoints
Handle refund requests and processing
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.marketplace import License, Transaction
from app.models.notifications import AuditLog, AuditAction, Notification, NotificationType
from app.models.user import User, UserRole

logger = structlog.get_logger()
router = APIRouter()


class RefundRequest(BaseModel):
    """Refund request from user"""
    license_id: UUID
    reason: str = Field(..., min_length=10, max_length=1000)


class RefundResponse(BaseModel):
    """Refund response"""
    refund_id: str
    status: str
    amount: float
    currency: str
    message: str


class RefundStatus(BaseModel):
    """Refund status check"""
    refund_id: str
    status: str
    amount: float
    created_at: datetime
    processed_at: Optional[datetime]


# Refund policy constants - loaded from config
REFUND_WINDOW_DAYS = settings.REFUND_WINDOW_DAYS
MAX_REFUNDS_PER_USER = settings.MAX_REFUNDS_PER_USER
MIN_PURCHASE_AGE_HOURS = settings.REFUND_COOLING_HOURS  # Prevent immediate refund abuse


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that requires admin role"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.post("/request", response_model=RefundResponse)
async def request_refund(
    request: RefundRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Request a refund for a purchased license.

    Refund policy:
    - Must be within 14 days of purchase
    - License must not have been used extensively
    - Maximum 3 refunds per user lifetime
    """
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Get the license
    license = await db.get(License, request.license_id)
    if not license:
        raise HTTPException(status_code=404, detail="License not found")

    if license.licensee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your license")

    # Check if already refunded
    if license.payment_status == "REFUNDED":
        raise HTTPException(status_code=400, detail="License already refunded")

    # Check refund window
    purchase_date = license.created_at
    if datetime.utcnow() - purchase_date > timedelta(days=REFUND_WINDOW_DAYS):
        raise HTTPException(
            status_code=400,
            detail=f"Refund window expired. Refunds must be requested within {REFUND_WINDOW_DAYS} days."
        )

    # Prevent immediate refund abuse
    if datetime.utcnow() - purchase_date < timedelta(hours=MIN_PURCHASE_AGE_HOURS):
        raise HTTPException(
            status_code=400,
            detail="Please wait at least 1 hour after purchase to request a refund."
        )

    # Check user's refund history
    refund_count = await db.scalar(
        select(func.count()).where(
            Transaction.user_id == current_user.id,
            Transaction.type == "REFUND",
        )
    ) or 0

    if refund_count >= MAX_REFUNDS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum refund limit ({MAX_REFUNDS_PER_USER}) reached. Please contact support."
        )

    # Get the original transaction
    original_transaction = await db.scalar(
        select(Transaction).where(
            Transaction.license_id == license.id,
            Transaction.type == "PURCHASE",
        )
    )

    if not original_transaction:
        raise HTTPException(status_code=400, detail="Original transaction not found")

    if not original_transaction.stripe_payment_intent_id:
        raise HTTPException(status_code=400, detail="No payment to refund")

    # Validate refund amount is reasonable
    MAX_REFUND_AMOUNT = 10000  # $10,000 max refund
    if original_transaction.amount_usd > MAX_REFUND_AMOUNT:
        logger.warning(
            "Large refund request requires manual review",
            amount=original_transaction.amount_usd,
            license_id=str(license.id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=400,
            detail=f"Refunds over ${MAX_REFUND_AMOUNT} require manual review. Please contact support@actorhub.ai"
        )

    try:
        # Process refund via Stripe
        refund = stripe.Refund.create(
            payment_intent=original_transaction.stripe_payment_intent_id,
            reason="requested_by_customer",
            metadata={
                "license_id": str(license.id),
                "user_id": str(current_user.id),
                "reason": request.reason[:200],  # Truncate for metadata limit
            }
        )

        # Update license status
        license.payment_status = "REFUNDED"
        license.is_active = False

        # Create refund transaction record
        refund_transaction = Transaction(
            user_id=current_user.id,
            license_id=license.id,
            type="REFUND",
            amount_usd=-original_transaction.amount_usd,  # Negative for refund
            currency=original_transaction.currency,
            stripe_payment_intent_id=refund.id,
            status="COMPLETED",
            transaction_metadata={
                "original_transaction_id": str(original_transaction.id),
                "refund_reason": request.reason,
            }
        )
        db.add(refund_transaction)

        # Create audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            action=AuditAction.REFUND,
            resource_type="license",
            resource_id=license.id,
            description=f"Refund requested: {request.reason[:100]}",
            success=True,
        )
        db.add(audit_log)

        # Notify license owner (the seller)
        if license.identity:
            seller_notification = Notification(
                user_id=license.identity.user_id,
                type=NotificationType.BILLING,
                title="License Refunded",
                message=f"A license for your identity was refunded. Amount: ${original_transaction.amount_usd}",
                extra_data={"license_id": str(license.id)},
            )
            db.add(seller_notification)

        await db.commit()

        logger.info(
            f"Refund processed successfully",
            refund_id=refund.id,
            user_id=str(current_user.id),
            license_id=str(license.id),
            amount=original_transaction.amount_usd,
        )

        return RefundResponse(
            refund_id=refund.id,
            status="succeeded",
            amount=original_transaction.amount_usd,
            currency=original_transaction.currency or "USD",
            message="Refund processed successfully. Funds will appear in 5-10 business days.",
        )

    except stripe.StripeError as e:
        logger.error(f"Stripe refund error: {e}")

        # Log failed attempt
        audit_log = AuditLog(
            user_id=current_user.id,
            action=AuditAction.REFUND,
            resource_type="license",
            resource_id=license.id,
            description=f"Refund failed: {str(e)}",
            success=False,
            error_message=str(e),
        )
        db.add(audit_log)
        await db.commit()

        raise HTTPException(status_code=400, detail=f"Refund failed: {str(e)}")


@router.get("/status/{refund_id}", response_model=RefundStatus)
async def get_refund_status(
    refund_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the status of a refund"""
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Get the transaction
    transaction = await db.scalar(
        select(Transaction).where(
            Transaction.stripe_payment_intent_id == refund_id,
            Transaction.type == "REFUND",
            Transaction.user_id == current_user.id,
        )
    )

    if not transaction:
        raise HTTPException(status_code=404, detail="Refund not found")

    try:
        # Get refund status from Stripe
        refund = stripe.Refund.retrieve(refund_id)

        return RefundStatus(
            refund_id=refund_id,
            status=refund.status,
            amount=abs(transaction.amount_usd),
            created_at=transaction.created_at,
            processed_at=datetime.fromtimestamp(refund.created) if refund.created else None,
        )
    except stripe.StripeError:
        # Return from database if Stripe fails
        return RefundStatus(
            refund_id=refund_id,
            status=transaction.status or "unknown",
            amount=abs(transaction.amount_usd),
            created_at=transaction.created_at,
            processed_at=None,
        )


@router.get("/history")
async def get_refund_history(
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's refund history"""
    query = select(Transaction).where(
        Transaction.user_id == current_user.id,
        Transaction.type == "REFUND",
    ).order_by(Transaction.created_at.desc())

    # Count total
    count_query = select(func.count()).where(
        Transaction.user_id == current_user.id,
        Transaction.type == "REFUND",
    )
    total = await db.scalar(count_query) or 0

    # Apply pagination
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    refunds = result.scalars().all()

    return {
        "refunds": [
            {
                "id": str(r.id),
                "refund_id": r.stripe_payment_intent_id,
                "amount": abs(r.amount_usd),
                "currency": r.currency,
                "status": r.status,
                "reason": r.transaction_metadata.get("refund_reason") if r.transaction_metadata else None,
                "created_at": r.created_at,
            }
            for r in refunds
        ],
        "total": total,
        "remaining_refunds": max(0, MAX_REFUNDS_PER_USER - total),
    }


@router.get("/policy")
async def get_refund_policy():
    """Get refund policy details"""
    return {
        "refund_window_days": REFUND_WINDOW_DAYS,
        "max_refunds_per_user": MAX_REFUNDS_PER_USER,
        "min_purchase_age_hours": MIN_PURCHASE_AGE_HOURS,
        "policy_summary": f"""
ActorHub.ai Refund Policy:

1. Refunds must be requested within {REFUND_WINDOW_DAYS} days of purchase.
2. Each user is limited to {MAX_REFUNDS_PER_USER} refunds lifetime.
3. Refunds cannot be requested within {MIN_PURCHASE_AGE_HOURS} hour(s) of purchase.
4. Refunds are processed within 5-10 business days.
5. Extensively used licenses may not be eligible for refund.

For disputes or special cases, contact support@actorhub.ai
        """.strip(),
    }


# Admin endpoints
@router.get("/admin/pending")
async def get_pending_refunds(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get pending refund requests (admin only)"""
    query = select(Transaction, User).join(User).where(
        Transaction.type == "REFUND",
        Transaction.status == "PENDING",
    ).order_by(Transaction.created_at)

    result = await db.execute(query)
    rows = result.all()

    return {
        "pending_refunds": [
            {
                "id": str(txn.id),
                "user_email": user.email,
                "amount": abs(txn.amount_usd),
                "reason": txn.transaction_metadata.get("refund_reason") if txn.transaction_metadata else None,
                "created_at": txn.created_at,
            }
            for txn, user in rows
        ]
    }
