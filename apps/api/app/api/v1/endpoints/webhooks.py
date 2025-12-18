"""
Webhook Endpoints
Handle webhooks from Stripe, Clerk, and other services
"""

import os
from datetime import datetime, timedelta

import structlog
import redis.asyncio as redis
from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from svix.webhooks import Webhook, WebhookVerificationError

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.identity import Identity
from app.models.marketplace import License, PaymentStatus, Transaction, TransactionType

logger = structlog.get_logger()
router = APIRouter()

# Redis client for idempotency (production-safe, multi-worker compatible)
_redis_client: redis.Redis = None
IDEMPOTENCY_TTL_SECONDS = 24 * 60 * 60  # 24 hours


async def get_redis_client() -> redis.Redis:
    """Get or create Redis client for idempotency checks"""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    return _redis_client


async def check_idempotency(event_id: str) -> bool:
    """
    Check if event was already processed using Redis SETNX.
    Returns True if already processed (should skip).

    This is safe for multi-worker deployments:
    - Uses Redis SETNX (SET if Not eXists) for atomic check-and-set
    - TTL ensures cleanup without manual management
    - Works across all API workers
    """
    try:
        redis_client = await get_redis_client()
        key = f"webhook:idempotency:{event_id}"

        # SETNX returns True if key was set (new event), False if already exists
        was_set = await redis_client.set(
            key,
            datetime.utcnow().isoformat(),
            nx=True,  # Only set if not exists
            ex=IDEMPOTENCY_TTL_SECONDS  # Auto-expire after 24 hours
        )

        if not was_set:
            logger.info(f"Duplicate webhook event (Redis): {event_id}")
            return True

        return False

    except redis.RedisError as e:
        # If Redis fails, log error but allow processing
        # Better to risk duplicate than to reject valid webhooks
        logger.error(f"Redis idempotency check failed: {e}. Allowing webhook processing.")
        return False


@router.post("/stripe")
async def stripe_webhook(
    request: Request, stripe_signature: str = Header(None, alias="Stripe-Signature")
):
    """
    Handle Stripe webhook events.

    Events handled:
    - checkout.session.completed: License purchase completed
    - payment_intent.succeeded: Payment confirmed
    - payment_intent.failed: Payment failed
    - customer.subscription.updated: Subscription changed
    - customer.subscription.deleted: Subscription cancelled
    """
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(500, "Stripe webhook secret not configured")

    payload = await request.body()

    # Verify signature
    try:
        import stripe

        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(400, f"Invalid signature: {str(e)}")

    # Idempotency check - skip if already processed
    event_id = event.get("id")
    if event_id and await check_idempotency(f"stripe:{event_id}"):
        return {"status": "already_processed"}

    async with async_session_maker() as db:
        try:
            event_type = event["type"]
            data = event["data"]["object"]

            if event_type == "checkout.session.completed":
                await handle_checkout_completed(db, data)

            elif event_type == "payment_intent.succeeded":
                await handle_payment_succeeded(db, data)

            elif event_type == "payment_intent.payment_failed":
                await handle_payment_failed(db, data)

            elif event_type == "customer.subscription.deleted":
                await handle_subscription_cancelled(db, data)

            # Stripe Connect events
            elif event_type == "account.updated":
                await handle_connect_account_updated(db, data)

            elif event_type == "account.application.deauthorized":
                await handle_connect_deauthorized(db, data)

            await db.commit()

        except Exception as e:
            await db.rollback()
            raise HTTPException(500, f"Webhook processing error: {str(e)}")

    return {"status": "received"}


async def handle_checkout_completed(db: AsyncSession, data: dict):
    """Handle completed checkout session"""
    _session_id = data.get("id")  # noqa: F841 - stored for logging/debugging
    payment_intent_id = data.get("payment_intent")
    metadata = data.get("metadata", {})

    license_id = metadata.get("license_id")
    if not license_id:
        return

    # Update license
    from sqlalchemy import select
    from app.models.user import User
    from app.services.email import get_email_service

    result = await db.execute(select(License).where(License.id == license_id))
    license = result.scalar_one_or_none()

    if license:
        license.payment_status = PaymentStatus.COMPLETED
        license.stripe_payment_intent_id = payment_intent_id
        license.paid_at = datetime.utcnow()
        license.is_active = True

        # Update identity stats
        identity = await db.get(Identity, license.identity_id)
        if identity:
            identity.total_licenses += 1
            identity.total_revenue += license.creator_payout_usd or 0

        # Create transaction record
        transaction = Transaction(
            license_id=license.id,
            user_id=license.licensee_id,
            type=TransactionType.PURCHASE,
            amount_usd=license.price_usd,
            status=PaymentStatus.COMPLETED,
            stripe_payment_intent_id=payment_intent_id,
            completed_at=datetime.utcnow(),
        )
        db.add(transaction)

        # Send email notifications
        email_service = get_email_service()

        # Email to buyer
        buyer = await db.get(User, license.licensee_id)
        if buyer and buyer.email:
            await email_service.send_license_purchase_email(
                to_email=buyer.email,
                name=buyer.display_name or buyer.first_name or "there",
                identity_name=identity.name if identity else "Unknown",
                license_type=license.license_type.value,
                price=license.price_usd,
            )

        # Email to creator
        if identity:
            creator = await db.get(User, identity.user_id)
            if creator and creator.email:
                await email_service.send_creator_sale_notification(
                    to_email=creator.email,
                    name=creator.display_name or creator.first_name or "Creator",
                    identity_name=identity.name,
                    license_type=license.license_type.value,
                    earnings=license.creator_payout_usd or 0,
                )


async def handle_payment_succeeded(db: AsyncSession, data: dict):
    """Handle successful payment"""
    payment_intent_id = data.get("id")

    from sqlalchemy import select

    result = await db.execute(
        select(License).where(License.stripe_payment_intent_id == payment_intent_id)
    )
    license = result.scalar_one_or_none()

    if license and license.payment_status != PaymentStatus.COMPLETED:
        license.payment_status = PaymentStatus.COMPLETED
        license.paid_at = datetime.utcnow()
        license.is_active = True


async def handle_payment_failed(db: AsyncSession, data: dict):
    """Handle failed payment"""
    payment_intent_id = data.get("id")
    _error = data.get("last_payment_error", {}).get("message", "Payment failed")  # noqa: F841

    from sqlalchemy import select

    result = await db.execute(
        select(License).where(License.stripe_payment_intent_id == payment_intent_id)
    )
    license = result.scalar_one_or_none()

    if license:
        license.payment_status = PaymentStatus.FAILED


async def handle_subscription_cancelled(db: AsyncSession, data: dict):
    """Handle subscription cancellation"""
    subscription_id = data.get("id")

    from sqlalchemy import select

    result = await db.execute(
        select(License).where(License.stripe_subscription_id == subscription_id)
    )
    license = result.scalar_one_or_none()

    if license:
        license.is_active = False
        license.valid_until = datetime.utcnow()


async def handle_connect_account_updated(db: AsyncSession, data: dict):
    """
    Handle Stripe Connect account updates.

    This is triggered when a creator's payout account status changes,
    such as when they complete onboarding or verification status updates.
    """
    from sqlalchemy import select
    from app.models.user import User

    account_id = data.get("id")
    details_submitted = data.get("details_submitted", False)
    payouts_enabled = data.get("payouts_enabled", False)

    # Find user with this Connect account
    result = await db.execute(
        select(User).where(User.stripe_connect_account_id == account_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"Connect account {account_id} not found in database")
        return

    logger.info(
        f"Connect account updated",
        account_id=account_id,
        user_id=str(user.id),
        details_submitted=details_submitted,
        payouts_enabled=payouts_enabled,
    )

    # Optionally send notification to user about account status changes
    if payouts_enabled:
        # Account is now fully set up for payouts
        from app.models.user import Notification, NotificationType

        notification = Notification(
            user_id=user.id,
            type=NotificationType.BILLING,
            title="Payout Account Ready",
            message="Your payout account is now fully set up. You can now receive earnings from your licensed identities.",
            action_url="/dashboard/settings",
        )
        db.add(notification)


async def handle_connect_deauthorized(db: AsyncSession, data: dict):
    """
    Handle Stripe Connect account deauthorization.

    This is triggered when a user disconnects their Stripe account
    from the platform.
    """
    from sqlalchemy import select
    from app.models.user import User

    account_id = data.get("account")

    result = await db.execute(
        select(User).where(User.stripe_connect_account_id == account_id)
    )
    user = result.scalar_one_or_none()

    if user:
        logger.info(f"Connect account deauthorized: {account_id} for user {user.id}")
        user.stripe_connect_account_id = None

        # Notify user
        from app.models.user import Notification, NotificationType

        notification = Notification(
            user_id=user.id,
            type=NotificationType.BILLING,
            title="Payout Account Disconnected",
            message="Your Stripe payout account has been disconnected. Set up a new account to continue receiving payouts.",
            action_url="/dashboard/settings",
        )
        db.add(notification)


@router.post("/clerk")
async def clerk_webhook(
    request: Request,
    svix_id: str = Header(None, alias="svix-id"),
    svix_timestamp: str = Header(None, alias="svix-timestamp"),
    svix_signature: str = Header(None, alias="svix-signature"),
):
    """
    Handle Clerk webhook events.

    Events handled:
    - user.created: New user signed up
    - user.updated: User info updated
    - user.deleted: User account deleted
    """
    if not settings.CLERK_WEBHOOK_SECRET:
        raise HTTPException(500, "Clerk webhook secret not configured")

    payload = await request.body()

    # Verify Clerk webhook signature using svix
    try:
        wh = Webhook(settings.CLERK_WEBHOOK_SECRET)
        headers = {
            "svix-id": svix_id,
            "svix-timestamp": svix_timestamp,
            "svix-signature": svix_signature,
        }
        event = wh.verify(payload, headers)
    except WebhookVerificationError:
        raise HTTPException(401, "Invalid webhook signature")
    except Exception:
        raise HTTPException(401, "Webhook verification failed")

    # Idempotency check - skip if already processed
    if svix_id and await check_idempotency(f"clerk:{svix_id}"):
        return {"status": "already_processed"}

    async with async_session_maker() as db:
        try:
            # event is already parsed by svix.verify()
            event_type = event.get("type")
            data = event.get("data", {})

            if event_type == "user.created":
                await handle_user_created(db, data)

            elif event_type == "user.updated":
                await handle_user_updated(db, data)

            elif event_type == "user.deleted":
                await handle_user_deleted(db, data)

            await db.commit()

        except Exception as e:
            await db.rollback()
            raise HTTPException(500, f"Webhook processing error: {str(e)}")

    return {"status": "received"}


async def handle_user_created(db: AsyncSession, data: dict):
    """Handle new user from Clerk"""
    from app.models.user import User

    clerk_id = data.get("id")
    email = data.get("email_addresses", [{}])[0].get("email_address")

    if not email:
        return

    # Check if user exists
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()

    if existing:
        existing.clerk_user_id = clerk_id
    else:
        user = User(
            email=email,
            clerk_user_id=clerk_id,
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            avatar_url=data.get("image_url"),
            email_verified=True,
        )
        db.add(user)


async def handle_user_updated(db: AsyncSession, data: dict):
    """Handle user update from Clerk"""
    from sqlalchemy import select

    from app.models.user import User

    clerk_id = data.get("id")
    result = await db.execute(select(User).where(User.clerk_user_id == clerk_id))
    user = result.scalar_one_or_none()

    if user:
        user.first_name = data.get("first_name") or user.first_name
        user.last_name = data.get("last_name") or user.last_name
        user.avatar_url = data.get("image_url") or user.avatar_url
        user.updated_at = datetime.utcnow()


async def handle_user_deleted(db: AsyncSession, data: dict):
    """Handle user deletion from Clerk"""
    from sqlalchemy import select

    from app.models.user import User

    clerk_id = data.get("id")
    result = await db.execute(select(User).where(User.clerk_user_id == clerk_id))
    user = result.scalar_one_or_none()

    if user:
        user.is_active = False
        user.updated_at = datetime.utcnow()


def verify_replicate_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify Replicate webhook signature using HMAC-SHA256.

    Replicate signs webhooks with HMAC-SHA256 using your webhook secret.
    The signature is passed in the X-Replicate-Signature or Webhook-Signature header.
    """
    import hmac
    import hashlib

    if not signature or not secret:
        return False

    try:
        # Replicate uses HMAC-SHA256
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Support both formats: raw hex or sha256=hex
        if signature.startswith('sha256='):
            signature = signature[7:]

        return hmac.compare_digest(expected_signature, signature)
    except Exception:
        return False


@router.post("/replicate")
async def replicate_webhook(
    request: Request,
    replicate_signature: str = Header(None, alias="X-Replicate-Signature"),
    webhook_signature: str = Header(None, alias="Webhook-Signature"),
):
    """
    Handle Replicate (training) webhook events.

    Events handled:
    - succeeded: Training completed successfully
    - failed: Training failed
    - processing: Training in progress

    Security: Validates HMAC-SHA256 signature if webhook secret is configured.
    """
    payload_bytes = await request.body()

    # Verify signature if secret is configured (production)
    if settings.REPLICATE_WEBHOOK_SECRET:
        signature = replicate_signature or webhook_signature
        if not signature:
            logger.warning("Replicate webhook missing signature header")
            raise HTTPException(401, "Missing webhook signature")

        if not verify_replicate_signature(
            payload_bytes,
            signature,
            settings.REPLICATE_WEBHOOK_SECRET
        ):
            logger.warning("Replicate webhook invalid signature")
            raise HTTPException(401, "Invalid webhook signature")

    payload = await request.json()

    # Idempotency check
    prediction_id = payload.get("id")
    if prediction_id and await check_idempotency(f"replicate:{prediction_id}"):
        return {"status": "already_processed"}

    status = payload.get("status")
    output = payload.get("output", {})
    error = payload.get("error")

    logger.info(
        f"Replicate webhook received",
        prediction_id=prediction_id,
        status=status,
    )

    async with async_session_maker() as db:
        try:
            if status == "succeeded":
                await handle_training_completed(db, prediction_id, output)
            elif status == "failed":
                await handle_training_failed(db, prediction_id, error)
            elif status == "processing":
                await handle_training_progress(db, prediction_id, payload)

            await db.commit()

        except Exception as e:
            await db.rollback()
            logger.error(f"Replicate webhook error: {e}")
            # Return 202 to acknowledge receipt even on error
            return {"status": "error", "message": str(e)}

    return {"status": "received"}


async def handle_training_completed(db: AsyncSession, prediction_id: str, output: dict):
    """Handle completed training from Replicate"""
    from sqlalchemy import select
    from app.models.identity import ActorPack, TrainingStatus, Identity
    from app.models.user import User
    from app.services.email import get_email_service

    weights_url = output.get("weights_url") or output.get("weights")

    # Find actor pack by prediction ID stored in metadata
    result = await db.execute(
        select(ActorPack).where(
            ActorPack.components.contains({"replicate_prediction_id": prediction_id})
        )
    )
    actor_pack = result.scalar_one_or_none()

    if actor_pack:
        actor_pack.training_status = TrainingStatus.COMPLETED
        actor_pack.training_completed_at = datetime.utcnow()
        actor_pack.lora_model_url = weights_url
        actor_pack.is_available = True
        logger.info(f"Training completed for actor pack {actor_pack.id}")

        # Send email notification to owner
        identity = await db.get(Identity, actor_pack.identity_id)
        if identity:
            user = await db.get(User, identity.user_id)
            if user and user.email:
                email_service = get_email_service()
                await email_service.send_training_complete_email(
                    to_email=user.email,
                    name=user.display_name or user.first_name or "Creator",
                    identity_name=identity.name,
                    quality_score=actor_pack.quality_score or 0,
                )


async def handle_training_failed(db: AsyncSession, prediction_id: str, error: str):
    """Handle failed training from Replicate"""
    from sqlalchemy import select
    from app.models.identity import ActorPack, TrainingStatus, Identity
    from app.models.user import User
    from app.services.email import get_email_service

    result = await db.execute(
        select(ActorPack).where(
            ActorPack.components.contains({"replicate_prediction_id": prediction_id})
        )
    )
    actor_pack = result.scalar_one_or_none()

    if actor_pack:
        actor_pack.training_status = TrainingStatus.FAILED
        actor_pack.training_error = error or "Training failed"
        logger.error(f"Training failed for actor pack {actor_pack.id}: {error}")

        # Send email notification to owner
        identity = await db.get(Identity, actor_pack.identity_id)
        if identity:
            user = await db.get(User, identity.user_id)
            if user and user.email:
                email_service = get_email_service()
                await email_service.send_training_failed_email(
                    to_email=user.email,
                    name=user.display_name or user.first_name or "Creator",
                    identity_name=identity.name,
                    error_message=error,
                )


async def handle_training_progress(db: AsyncSession, prediction_id: str, payload: dict):
    """Handle training progress update from Replicate"""
    from sqlalchemy import select
    from app.models.identity import ActorPack, TrainingStatus

    result = await db.execute(
        select(ActorPack).where(
            ActorPack.components.contains({"replicate_prediction_id": prediction_id})
        )
    )
    actor_pack = result.scalar_one_or_none()

    if actor_pack:
        actor_pack.training_status = TrainingStatus.PROCESSING
        # Extract progress if available
        logs = payload.get("logs", "")
        if "%" in logs:
            try:
                # Try to parse progress from logs
                import re
                match = re.search(r"(\d+)%", logs)
                if match:
                    actor_pack.training_progress = int(match.group(1))
            except Exception:
                pass
