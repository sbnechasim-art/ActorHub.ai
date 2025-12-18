"""
Admin Endpoints
Dashboard and management for administrators
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.identity import Identity, ActorPack, UsageLog
from app.models.marketplace import License, Transaction
from app.models.notifications import AuditLog, WebhookEvent, Subscription, Payout
from app.models.user import User, UserRole, UserTier

logger = structlog.get_logger()
router = APIRouter()


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that requires admin role"""
    if current_user.role != UserRole.ADMIN:
        logger.warning(
            f"Admin access denied for user {current_user.id}",
            user_id=str(current_user.id),
            role=current_user.role.value if current_user.role else "None",
        )
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )
    return current_user


class DashboardStats(BaseModel):
    """Dashboard statistics"""
    total_users: int
    active_users: int
    total_identities: int
    total_actor_packs: int
    total_revenue: float
    revenue_this_month: float
    api_calls_today: int
    active_subscriptions: int


class UserSummary(BaseModel):
    """User summary for admin list"""
    id: UUID
    email: str
    display_name: Optional[str]
    role: str
    tier: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime]


class AuditLogEntry(BaseModel):
    """Audit log entry"""
    id: UUID
    user_email: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[UUID]
    description: Optional[str]
    ip_address: Optional[str]
    success: bool
    created_at: datetime


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get admin dashboard statistics"""
    # Total users
    total_users = await db.scalar(select(func.count()).select_from(User)) or 0

    # Active users (logged in last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    active_users = await db.scalar(
        select(func.count()).where(
            User.last_login_at >= thirty_days_ago,
            User.is_active == True,
        )
    ) or 0

    # Total identities
    total_identities = await db.scalar(
        select(func.count()).where(Identity.deleted_at.is_(None))
    ) or 0

    # Total actor packs
    total_actor_packs = await db.scalar(select(func.count()).select_from(ActorPack)) or 0

    # Total revenue
    total_revenue = await db.scalar(
        select(func.sum(Transaction.amount_usd)).where(
            Transaction.type == "PURCHASE"
        )
    ) or 0.0

    # Revenue this month
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    revenue_this_month = await db.scalar(
        select(func.sum(Transaction.amount_usd)).where(
            Transaction.type == "PURCHASE",
            Transaction.created_at >= month_start,
        )
    ) or 0.0

    # API calls today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    api_calls_today = await db.scalar(
        select(func.count()).where(UsageLog.created_at >= today_start)
    ) or 0

    # Active subscriptions
    active_subscriptions = await db.scalar(
        select(func.count()).where(Subscription.status == "ACTIVE")
    ) or 0

    return DashboardStats(
        total_users=total_users,
        active_users=active_users,
        total_identities=total_identities,
        total_actor_packs=total_actor_packs,
        total_revenue=float(total_revenue),
        revenue_this_month=float(revenue_this_month),
        api_calls_today=api_calls_today,
        active_subscriptions=active_subscriptions,
    )


@router.get("/users")
async def list_users(
    role: Optional[UserRole] = None,
    tier: Optional[UserTier] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users with filtering"""
    query = select(User)

    if role:
        query = query.where(User.role == role)
    if tier:
        query = query.where(User.tier == tier)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if search:
        query = query.where(
            User.email.ilike(f"%{search}%") |
            User.display_name.ilike(f"%{search}%")
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply pagination
    query = query.order_by(desc(User.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    return {
        "users": [
            UserSummary(
                id=u.id,
                email=u.email,
                display_name=u.display_name,
                role=u.role.value if u.role else "USER",
                tier=u.tier.value if u.tier else "FREE",
                is_active=u.is_active or False,
                created_at=u.created_at,
                last_login_at=u.last_login_at,
            )
            for u in users
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed user information"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get user's identities count
    identities_count = await db.scalar(
        select(func.count()).where(
            Identity.user_id == user_id,
            Identity.deleted_at.is_(None),
        )
    ) or 0

    # Get user's transactions
    transactions_total = await db.scalar(
        select(func.sum(Transaction.amount_usd)).where(Transaction.user_id == user_id)
    ) or 0.0

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role.value if user.role else "USER",
            "tier": user.tier.value if user.tier else "FREE",
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "email_verified": user.email_verified,
            "created_at": user.created_at,
            "last_login_at": user.last_login_at,
            "stripe_customer_id": user.stripe_customer_id,
        },
        "stats": {
            "identities_count": identities_count,
            "total_spent": float(transactions_total),
        },
    }


@router.patch("/users/{user_id}")
async def update_user(
    user_id: UUID,
    role: Optional[UserRole] = None,
    tier: Optional[UserTier] = None,
    is_active: Optional[bool] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update user (admin only)"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent self-demotion
    if user.id == admin.id and role and role != UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Cannot demote yourself")

    if role is not None:
        user.role = role
    if tier is not None:
        user.tier = tier
    if is_active is not None:
        user.is_active = is_active

    await db.commit()

    logger.info(
        f"Admin updated user {user_id}",
        admin_id=str(admin.id),
        user_id=str(user_id),
        changes={"role": role, "tier": tier, "is_active": is_active},
    )

    return {"status": "success", "message": "User updated"}


@router.get("/audit-logs")
async def get_audit_logs(
    user_id: Optional[UUID] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get audit logs"""
    query = select(AuditLog, User).outerjoin(User, AuditLog.user_id == User.id)

    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)

    # Count total
    count_query = select(func.count()).select_from(AuditLog)
    if user_id:
        count_query = count_query.where(AuditLog.user_id == user_id)
    if action:
        count_query = count_query.where(AuditLog.action == action)
    total = await db.scalar(count_query) or 0

    query = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    return {
        "logs": [
            AuditLogEntry(
                id=log.id,
                user_email=user.email if user else None,
                action=log.action.value if log.action else "UNKNOWN",
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                description=log.description,
                ip_address=log.ip_address,
                success=log.success or False,
                created_at=log.created_at,
            )
            for log, user in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/webhooks")
async def get_webhook_events(
    source: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get webhook events for debugging"""
    query = select(WebhookEvent)

    if source:
        query = query.where(WebhookEvent.source == source)
    if status:
        query = query.where(WebhookEvent.status == status)

    # Count total
    count_query = select(func.count()).select_from(WebhookEvent)
    total = await db.scalar(count_query) or 0

    query = query.order_by(desc(WebhookEvent.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    events = result.scalars().all()

    return {
        "events": [
            {
                "id": e.id,
                "event_id": e.event_id,
                "source": e.source.value if e.source else "UNKNOWN",
                "event_type": e.event_type,
                "status": e.status.value if e.status else "PENDING",
                "attempts": e.attempts,
                "error_message": e.error_message,
                "created_at": e.created_at,
            }
            for e in events
        ],
        "total": total,
    }


@router.post("/webhooks/{event_id}/retry")
async def retry_webhook(
    event_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed webhook event"""
    event = await db.get(WebhookEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Webhook event not found")

    # Reset status for retry
    from app.models.notifications import WebhookEventStatus
    event.status = WebhookEventStatus.PENDING
    event.error_message = None
    await db.commit()

    # In production, would queue for processing
    return {"status": "success", "message": "Webhook queued for retry"}


@router.get("/payouts/pending")
async def get_pending_payouts(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get pending creator payouts"""
    from app.models.notifications import PayoutStatus

    query = select(Payout, User).join(User).where(
        Payout.status == PayoutStatus.PENDING
    ).order_by(Payout.requested_at)

    result = await db.execute(query)
    rows = result.all()

    return {
        "payouts": [
            {
                "id": payout.id,
                "user_email": user.email,
                "amount": payout.amount,
                "currency": payout.currency,
                "method": payout.method.value if payout.method else "STRIPE_CONNECT",
                "transaction_count": payout.transaction_count,
                "requested_at": payout.requested_at,
            }
            for payout, user in rows
        ]
    }


@router.post("/payouts/{payout_id}/approve")
async def approve_payout(
    payout_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Approve and process a payout via Stripe Connect"""
    import stripe
    from app.core.config import settings
    from app.models.notifications import PayoutStatus

    payout = await db.get(Payout, payout_id)
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")

    if payout.status != PayoutStatus.PENDING:
        raise HTTPException(status_code=400, detail="Payout is not pending")

    # Get the user to find their Stripe Connect account
    user = await db.get(User, payout.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.stripe_connect_account_id:
        raise HTTPException(
            status_code=400,
            detail="User has not connected their Stripe account for payouts"
        )

    # Verify Stripe is configured
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="Stripe is not configured on the server"
        )

    # Mark as processing before API call
    payout.status = PayoutStatus.PROCESSING
    payout.processed_at = datetime.utcnow()
    await db.commit()

    try:
        # Initialize Stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        # Create a transfer to the connected account
        transfer = stripe.Transfer.create(
            amount=int(payout.amount * 100),  # Convert to cents
            currency=payout.currency.lower(),
            destination=user.stripe_connect_account_id,
            transfer_group=f"payout_{payout_id}",
            metadata={
                "payout_id": str(payout_id),
                "user_id": str(user.id),
                "admin_id": str(admin.id),
            }
        )

        # Update payout with Stripe transfer ID
        payout.stripe_transfer_id = transfer.id
        payout.status = PayoutStatus.COMPLETED
        payout.completed_at = datetime.utcnow()
        await db.commit()

        logger.info(
            f"Payout {payout_id} completed via Stripe",
            payout_id=str(payout_id),
            admin_id=str(admin.id),
            amount=payout.amount,
            stripe_transfer_id=transfer.id,
        )

        return {
            "status": "success",
            "message": "Payout completed",
            "stripe_transfer_id": transfer.id
        }

    except stripe.error.StripeError as e:
        # Rollback to pending on failure
        payout.status = PayoutStatus.FAILED
        payout.error_message = str(e)
        await db.commit()

        logger.error(
            f"Stripe payout failed for {payout_id}",
            payout_id=str(payout_id),
            error=str(e),
        )

        raise HTTPException(
            status_code=400,
            detail=f"Stripe transfer failed: {str(e)}"
        )
