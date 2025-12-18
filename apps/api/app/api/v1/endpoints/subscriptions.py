"""
Subscription Endpoints
Billing and subscription management
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.notifications import Subscription, SubscriptionPlan, SubscriptionStatus
from app.models.user import User, UserTier

logger = structlog.get_logger()
router = APIRouter()


class SubscriptionResponse(BaseModel):
    """Subscription details"""
    id: UUID
    plan: str
    status: str
    amount: float
    currency: str
    interval: Optional[str]
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool
    identities_limit: int
    api_calls_limit: int
    storage_limit_mb: int

    class Config:
        from_attributes = True


class PlanInfo(BaseModel):
    """Plan information"""
    id: str
    name: str
    price_monthly: float
    price_yearly: float
    identities_limit: int
    api_calls_limit: int
    storage_limit_mb: int
    features: list


class CreateCheckoutRequest(BaseModel):
    """Request to create checkout session"""
    plan: SubscriptionPlan
    interval: str = "month"  # "month" or "year"
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutResponse(BaseModel):
    """Checkout session response"""
    checkout_url: str
    session_id: str


# Plan configurations
PLANS = {
    SubscriptionPlan.FREE: {
        "name": "Free",
        "price_monthly": 0,
        "price_yearly": 0,
        "identities_limit": 3,
        "api_calls_limit": 100,
        "storage_limit_mb": 50,
        "features": ["3 protected identities", "100 API calls/month", "Basic support"],
    },
    SubscriptionPlan.PRO_MONTHLY: {
        "name": "Pro",
        "price_monthly": 29,
        "price_yearly": 290,
        "identities_limit": 25,
        "api_calls_limit": 10000,
        "storage_limit_mb": 1000,
        "features": [
            "25 protected identities",
            "10,000 API calls/month",
            "Priority support",
            "Voice cloning",
            "LoRA training",
        ],
    },
    SubscriptionPlan.ENTERPRISE_MONTHLY: {
        "name": "Enterprise",
        "price_monthly": 199,
        "price_yearly": 1990,
        "identities_limit": -1,  # Unlimited
        "api_calls_limit": 100000,
        "storage_limit_mb": 10000,
        "features": [
            "Unlimited identities",
            "100,000 API calls/month",
            "Dedicated support",
            "Custom integrations",
            "SLA guarantee",
            "White-label options",
        ],
    },
}


@router.get("/current", response_model=Optional[SubscriptionResponse])
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's current subscription"""
    query = select(Subscription).where(
        Subscription.user_id == current_user.id,
        Subscription.status.in_([
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
            SubscriptionStatus.PAST_DUE,
        ]),
    ).order_by(Subscription.created_at.desc())

    result = await db.execute(query)
    subscription = result.scalar_one_or_none()

    if not subscription:
        return None

    return SubscriptionResponse(
        id=subscription.id,
        plan=subscription.plan.value,
        status=subscription.status.value,
        amount=subscription.amount or 0,
        currency=subscription.currency or "USD",
        interval=subscription.interval,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end or False,
        identities_limit=subscription.identities_limit or 3,
        api_calls_limit=subscription.api_calls_limit or 1000,
        storage_limit_mb=subscription.storage_limit_mb or 100,
    )


@router.get("/plans")
async def get_available_plans():
    """Get all available subscription plans"""
    plans = []
    for plan_id, plan_info in PLANS.items():
        plans.append(
            PlanInfo(
                id=plan_id.value,
                name=plan_info["name"],
                price_monthly=plan_info["price_monthly"],
                price_yearly=plan_info["price_yearly"],
                identities_limit=plan_info["identities_limit"],
                api_calls_limit=plan_info["api_calls_limit"],
                storage_limit_mb=plan_info["storage_limit_mb"],
                features=plan_info["features"],
            )
        )
    return {"plans": plans}


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    request: CreateCheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe checkout session for subscription"""
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY

    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Payment system not configured")

    # Get plan details
    plan_info = PLANS.get(request.plan)
    if not plan_info:
        raise HTTPException(status_code=400, detail="Invalid plan")

    # Determine price based on interval
    if request.interval == "year":
        price_amount = int(plan_info["price_yearly"] * 100)  # Stripe uses cents
    else:
        price_amount = int(plan_info["price_monthly"] * 100)

    if price_amount == 0:
        raise HTTPException(status_code=400, detail="Cannot checkout free plan")

    try:
        # Create or get Stripe customer
        if not current_user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.full_name,
                metadata={"user_id": str(current_user.id)},
            )
            current_user.stripe_customer_id = customer.id
            await db.commit()
        else:
            customer = stripe.Customer.retrieve(current_user.stripe_customer_id)

        # Create checkout session
        success_url = request.success_url or f"{settings.FRONTEND_URL}/billing/success"
        cancel_url = request.cancel_url or f"{settings.FRONTEND_URL}/billing/cancel"

        session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=["card"],
            mode="subscription",
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": price_amount,
                        "recurring": {"interval": request.interval},
                        "product_data": {
                            "name": f"ActorHub.ai {plan_info['name']} Plan",
                            "description": ", ".join(plan_info["features"][:3]),
                        },
                    },
                    "quantity": 1,
                }
            ],
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata={
                "user_id": str(current_user.id),
                "plan": request.plan.value,
                "interval": request.interval,
            },
        )

        return CheckoutResponse(
            checkout_url=session.url,
            session_id=session.id,
        )

    except stripe.StripeError as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel subscription at period end"""
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Get current subscription
    query = select(Subscription).where(
        Subscription.user_id == current_user.id,
        Subscription.status == SubscriptionStatus.ACTIVE,
    )
    result = await db.execute(query)
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")

    try:
        # Cancel on Stripe
        if subscription.stripe_subscription_id:
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True,
            )

        subscription.cancel_at_period_end = True
        await db.commit()

        return {
            "status": "success",
            "message": "Subscription will be canceled at the end of the billing period",
            "period_end": subscription.current_period_end,
        }

    except stripe.StripeError as e:
        logger.error(f"Stripe error canceling subscription: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reactivate")
async def reactivate_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reactivate a canceled subscription"""
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Get subscription marked for cancellation
    query = select(Subscription).where(
        Subscription.user_id == current_user.id,
        Subscription.cancel_at_period_end == True,
    )
    result = await db.execute(query)
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(status_code=404, detail="No canceled subscription found")

    try:
        # Reactivate on Stripe
        if subscription.stripe_subscription_id:
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=False,
            )

        subscription.cancel_at_period_end = False
        await db.commit()

        return {
            "status": "success",
            "message": "Subscription reactivated",
        }

    except stripe.StripeError as e:
        logger.error(f"Stripe error reactivating subscription: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/usage")
async def get_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current billing period usage"""
    from sqlalchemy import func
    from app.models.identity import Identity, UsageLog

    # Get subscription limits
    query = select(Subscription).where(
        Subscription.user_id == current_user.id,
        Subscription.status == SubscriptionStatus.ACTIVE,
    )
    result = await db.execute(query)
    subscription = result.scalar_one_or_none()

    # Default limits for free tier
    limits = {
        "identities": 3,
        "api_calls": 100,
        "storage_mb": 50,
    }

    if subscription:
        limits = {
            "identities": subscription.identities_limit,
            "api_calls": subscription.api_calls_limit,
            "storage_mb": subscription.storage_limit_mb,
        }

    # Count identities
    identity_count = await db.scalar(
        select(func.count()).where(
            Identity.user_id == current_user.id,
            Identity.deleted_at.is_(None),
        )
    ) or 0

    # Count API calls this period
    period_start = subscription.current_period_start if subscription else None
    if period_start:
        api_calls = await db.scalar(
            select(func.count()).where(
                UsageLog.requester_id == current_user.id,
                UsageLog.created_at >= period_start,
            )
        ) or 0
    else:
        # For free tier, count from start of month
        from datetime import datetime
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        api_calls = await db.scalar(
            select(func.count()).where(
                UsageLog.requester_id == current_user.id,
                UsageLog.created_at >= month_start,
            )
        ) or 0

    return {
        "usage": {
            "identities": identity_count,
            "api_calls": api_calls,
            "storage_mb": 0,  # Would calculate from file sizes
        },
        "limits": limits,
        "period_start": subscription.current_period_start if subscription else None,
        "period_end": subscription.current_period_end if subscription else None,
    }
