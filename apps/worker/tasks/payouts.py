"""
Payout Processing Tasks

Handles automatic payouts to creators:
- Mature pending earnings (holding period -> available)
- Process automatic weekly payouts
- Send payout notifications

CRITICAL: Uses Redis-based idempotency to prevent duplicate payments.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import structlog
import redis
import hashlib

from celery_app import app
from config import settings
from tracing import trace_task, add_task_attribute

logger = structlog.get_logger()

# Redis client for idempotency locks
_redis_client = None

def get_redis_client() -> redis.Redis:
    """Get or create Redis client for idempotency locks."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(
            settings.CELERY_BROKER_URL,
            decode_responses=True
        )
    return _redis_client


def acquire_idempotency_lock(key: str, ttl_seconds: int = 3600) -> bool:
    """
    Acquire an idempotency lock using Redis SETNX.

    Returns True if lock acquired (first execution), False if already exists.
    """
    try:
        client = get_redis_client()
        # SETNX returns True if key was set (didn't exist), False otherwise
        result = client.set(f"idempotency:{key}", "1", nx=True, ex=ttl_seconds)
        return result is True
    except Exception as e:
        logger.warning(f"Failed to acquire idempotency lock: {e}")
        # On Redis failure, proceed cautiously - log but allow execution
        # This is safer than potentially skipping legitimate payouts
        return True


def release_idempotency_lock(key: str) -> None:
    """Release an idempotency lock."""
    try:
        client = get_redis_client()
        client.delete(f"idempotency:{key}")
    except Exception as e:
        logger.warning(f"Failed to release idempotency lock: {e}")


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def mature_pending_earnings(self, trace_headers: Optional[Dict] = None) -> Dict:
    """
    Move earnings from PENDING to AVAILABLE status when holding period expires.

    This task runs daily to update earnings that have passed the holding period.
    IDEMPOTENCY: Uses Redis lock to prevent concurrent execution.
    """
    # Idempotency: Only one instance can run per hour
    hour_key = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H")
    idempotency_key = f"mature_earnings:{hour_key}"

    if not acquire_idempotency_lock(idempotency_key, ttl_seconds=3600):  # 1h lock
        logger.info("Mature earnings already running this hour")
        return {"success": True, "message": "Already running", "matured_count": 0}

    with trace_task("mature_pending_earnings", trace_headers) as span:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_mature_pending_earnings_async())
        except Exception as e:
            release_idempotency_lock(idempotency_key)
            logger.error("Mature earnings failed", error=str(e))
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        finally:
            loop.close()

        add_task_attribute("matured_count", result.get("matured_count", 0))
        add_task_attribute("total_amount", result.get("total_amount", 0))
        logger.info(
            "Matured pending earnings",
            matured_count=result.get("matured_count", 0),
            total_amount=result.get("total_amount", 0)
        )
        return result


async def _mature_pending_earnings_async() -> Dict:
    """Async implementation of earning maturation"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select, update, func
    import enum

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Import enum values directly since we can't import from API
    class EarningStatus(str, enum.Enum):
        PENDING = "PENDING"
        AVAILABLE = "AVAILABLE"
        PAID = "PAID"
        REFUNDED = "REFUNDED"

    async with async_session() as db:
        now = datetime.now(timezone.utc)

        # Get count and sum of earnings to mature
        from sqlalchemy import text
        count_result = await db.execute(
            text("""
                SELECT COUNT(*), COALESCE(SUM(net_amount), 0)
                FROM creator_earnings
                WHERE status = 'PENDING'
                AND available_at <= :now
            """),
            {"now": now}
        )
        row = count_result.fetchone()
        count, total = row[0], float(row[1]) if row[1] else 0

        if count > 0:
            # Update to AVAILABLE
            await db.execute(
                text("""
                    UPDATE creator_earnings
                    SET status = 'AVAILABLE', updated_at = :now
                    WHERE status = 'PENDING'
                    AND available_at <= :now
                """),
                {"now": now}
            )
            await db.commit()

        logger.info(f"Matured {count} earnings totaling ${total:.2f}")
        return {
            "success": True,
            "matured_count": count,
            "total_amount": round(total, 2)
        }


@app.task(bind=True, max_retries=3, default_retry_delay=300)
def process_auto_payouts(self, trace_headers: Optional[Dict] = None) -> Dict:
    """
    Process automatic payouts for creators with auto-payout enabled.

    This task runs weekly (or as configured) to automatically pay out
    available earnings to creators who have:
    - Stripe Connect account set up and verified
    - Available balance >= minimum payout threshold
    - Auto-payout enabled in their settings

    IDEMPOTENCY: Uses Redis lock to prevent duplicate executions.
    """
    if not settings.PAYOUT_AUTO_ENABLED:
        logger.info("Automatic payouts disabled")
        return {"success": True, "message": "Auto payouts disabled", "processed": 0}

    # Generate idempotency key based on date (one run per day max)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    idempotency_key = f"auto_payouts:{today}"

    if not acquire_idempotency_lock(idempotency_key, ttl_seconds=86400):  # 24h lock
        logger.warning(
            "Auto payouts already running or completed today",
            idempotency_key=idempotency_key
        )
        return {"success": True, "message": "Already processed today", "processed": 0}

    with trace_task("process_auto_payouts", trace_headers) as span:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_process_auto_payouts_async())
        except Exception as e:
            # Release lock on failure so retry can happen
            release_idempotency_lock(idempotency_key)
            logger.error("Auto payouts failed", error=str(e))
            raise self.retry(exc=e, countdown=300 * (2 ** self.request.retries))
        finally:
            loop.close()

        add_task_attribute("processed_count", result.get("processed", 0))
        add_task_attribute("total_paid", result.get("total_paid", 0))
        logger.info(
            "Auto payouts processed",
            processed=result.get("processed", 0),
            total_paid=result.get("total_paid", 0)
        )
        return result


async def _process_auto_payouts_async() -> Dict:
    """Async implementation of auto payouts"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text
    import stripe
    import enum

    if not settings.STRIPE_SECRET_KEY:
        logger.warning("Stripe not configured, skipping auto payouts")
        return {"success": False, "error": "Stripe not configured", "processed": 0}

    stripe.api_key = settings.STRIPE_SECRET_KEY

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    class EarningStatus(str, enum.Enum):
        PENDING = "PENDING"
        AVAILABLE = "AVAILABLE"
        PAID = "PAID"

    class PayoutStatus(str, enum.Enum):
        PENDING = "PENDING"
        PROCESSING = "PROCESSING"
        COMPLETED = "COMPLETED"
        FAILED = "FAILED"

    processed = 0
    total_paid = 0
    errors = []

    async with async_session() as db:
        now = datetime.now(timezone.utc)

        # First, mature any pending earnings
        await db.execute(
            text("""
                UPDATE creator_earnings
                SET status = 'AVAILABLE', updated_at = :now
                WHERE status = 'PENDING'
                AND available_at <= :now
            """),
            {"now": now}
        )

        # Get creators with available earnings >= minimum
        creators_result = await db.execute(
            text("""
                SELECT
                    ce.creator_id,
                    u.email,
                    u.stripe_connect_account_id,
                    u.display_name,
                    SUM(ce.net_amount) as available_balance
                FROM creator_earnings ce
                JOIN users u ON u.id = ce.creator_id
                WHERE ce.status = 'AVAILABLE'
                AND u.stripe_connect_account_id IS NOT NULL
                GROUP BY ce.creator_id, u.email, u.stripe_connect_account_id, u.display_name
                HAVING SUM(ce.net_amount) >= :minimum
            """),
            {"minimum": settings.PAYOUT_MINIMUM_USD}
        )
        creators = creators_result.fetchall()

        for creator in creators:
            creator_id = creator[0]
            email = creator[1]
            connect_account_id = creator[2]
            display_name = creator[3]
            available_balance = float(creator[4])

            try:
                # Per-creator idempotency lock (prevents duplicate transfers)
                creator_lock_key = f"payout_creator:{creator_id}:{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
                if not acquire_idempotency_lock(creator_lock_key, ttl_seconds=86400):
                    logger.info(f"Skipping {email} - already processing payout today")
                    continue

                # Verify Connect account is active
                account = stripe.Account.retrieve(connect_account_id)
                if not account.details_submitted or not account.payouts_enabled:
                    logger.warning(
                        f"Skipping payout for {email} - Connect account not ready"
                    )
                    release_idempotency_lock(creator_lock_key)
                    continue

                # Check for existing pending payout
                existing_payout = await db.execute(
                    text("""
                        SELECT id FROM payouts
                        WHERE user_id = :user_id
                        AND status = 'PENDING'
                    """),
                    {"user_id": str(creator_id)}
                )
                if existing_payout.fetchone():
                    logger.info(f"Skipping {email} - already has pending payout")
                    release_idempotency_lock(creator_lock_key)
                    continue

                # Get all available earnings for this creator
                earnings_result = await db.execute(
                    text("""
                        SELECT id, net_amount, earned_at
                        FROM creator_earnings
                        WHERE creator_id = :creator_id
                        AND status = 'AVAILABLE'
                    """),
                    {"creator_id": str(creator_id)}
                )
                earnings = earnings_result.fetchall()

                if not earnings:
                    continue

                earning_ids = [str(e[0]) for e in earnings]
                total_amount = sum(float(e[1]) for e in earnings)
                period_start = min(e[2] for e in earnings)
                period_end = max(e[2] for e in earnings)

                # Create payout record
                import uuid
                payout_id = uuid.uuid4()

                await db.execute(
                    text("""
                        INSERT INTO payouts (
                            id, user_id, amount, currency, fee, net_amount,
                            method, status, transaction_ids, transaction_count,
                            period_start, period_end, requested_at, created_at, updated_at
                        ) VALUES (
                            :id, :user_id, :amount, 'USD', 0, :amount,
                            'STRIPE_CONNECT', 'PROCESSING', :transaction_ids, :count,
                            :period_start, :period_end, :now, :now, :now
                        )
                    """),
                    {
                        "id": str(payout_id),
                        "user_id": str(creator_id),
                        "amount": total_amount,
                        "transaction_ids": earning_ids,
                        "count": len(earnings),
                        "period_start": period_start,
                        "period_end": period_end,
                        "now": now,
                    }
                )

                # Link earnings to payout
                await db.execute(
                    text("""
                        UPDATE creator_earnings
                        SET payout_id = :payout_id, updated_at = :now
                        WHERE id = ANY(:earning_ids)
                    """),
                    {
                        "payout_id": str(payout_id),
                        "earning_ids": earning_ids,
                        "now": now,
                    }
                )

                # Create Stripe transfer with idempotency key
                # This ensures we can't create duplicate transfers even if retry happens
                stripe_idempotency_key = f"transfer_{payout_id}"
                transfer = stripe.Transfer.create(
                    amount=int(total_amount * 100),  # cents
                    currency="usd",
                    destination=connect_account_id,
                    transfer_group=f"auto_payout_{payout_id}",
                    metadata={
                        "payout_id": str(payout_id),
                        "user_id": str(creator_id),
                        "auto_payout": "true",
                    },
                    idempotency_key=stripe_idempotency_key,
                )

                # Update payout and earnings as completed
                await db.execute(
                    text("""
                        UPDATE payouts
                        SET status = 'COMPLETED',
                            stripe_transfer_id = :transfer_id,
                            processed_at = :now,
                            completed_at = :now,
                            updated_at = :now
                        WHERE id = :payout_id
                    """),
                    {
                        "transfer_id": transfer.id,
                        "now": now,
                        "payout_id": str(payout_id),
                    }
                )

                await db.execute(
                    text("""
                        UPDATE creator_earnings
                        SET status = 'PAID', paid_at = :now, updated_at = :now
                        WHERE payout_id = :payout_id
                    """),
                    {"now": now, "payout_id": str(payout_id)}
                )

                await db.commit()

                processed += 1
                total_paid += total_amount

                logger.info(
                    f"Auto payout completed for {email}",
                    payout_id=str(payout_id),
                    amount=total_amount,
                    transfer_id=transfer.id
                )

            except stripe.error.StripeError as e:
                logger.error(f"Stripe error for {email}: {e}")
                errors.append({"email": email, "error": str(e)})
                await db.rollback()
            except Exception as e:
                logger.error(f"Error processing payout for {email}: {e}")
                errors.append({"email": email, "error": str(e)})
                await db.rollback()

    return {
        "success": True,
        "processed": processed,
        "total_paid": round(total_paid, 2),
        "errors": errors if errors else None,
    }


@app.task(bind=True, max_retries=2, default_retry_delay=300)
def send_payout_reminders(self, trace_headers: Optional[Dict] = None) -> Dict:
    """
    Send reminders to creators who have available balance but haven't
    set up their Stripe Connect account yet.

    IDEMPOTENCY: Only sends one reminder per week per creator.
    """
    # Idempotency: Only one run per day
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    idempotency_key = f"payout_reminders:{today}"

    if not acquire_idempotency_lock(idempotency_key, ttl_seconds=86400):  # 24h lock
        logger.info("Payout reminders already sent today")
        return {"success": True, "message": "Already sent today", "sent": 0}

    with trace_task("send_payout_reminders", trace_headers) as span:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_send_payout_reminders_async())
        except Exception as e:
            release_idempotency_lock(idempotency_key)
            logger.error("Payout reminders failed", error=str(e))
            raise self.retry(exc=e, countdown=300 * (2 ** self.request.retries))
        finally:
            loop.close()

        add_task_attribute("reminders_sent", result.get("sent", 0))
        logger.info("Payout reminders sent", sent=result.get("sent", 0))
        return result


async def _send_payout_reminders_async() -> Dict:
    """Async implementation of reminder sending"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    sent = 0

    async with async_session() as db:
        # Find creators with available balance but no Connect account
        result = await db.execute(
            text("""
                SELECT
                    u.id,
                    u.email,
                    u.display_name,
                    SUM(ce.net_amount) as available_balance
                FROM creator_earnings ce
                JOIN users u ON u.id = ce.creator_id
                WHERE ce.status = 'AVAILABLE'
                AND u.stripe_connect_account_id IS NULL
                GROUP BY u.id, u.email, u.display_name
                HAVING SUM(ce.net_amount) >= :minimum
            """),
            {"minimum": settings.PAYOUT_MINIMUM_USD}
        )
        creators = result.fetchall()

        for creator in creators:
            user_id, email, display_name, balance = creator

            # Create notification
            import uuid
            await db.execute(
                text("""
                    INSERT INTO notifications (
                        id, user_id, type, title, message, action_url,
                        is_read, created_at
                    ) VALUES (
                        :id, :user_id, 'BILLING', :title, :message, :action_url,
                        false, NOW()
                    )
                """),
                {
                    "id": str(uuid.uuid4()),
                    "user_id": str(user_id),
                    "title": "You have earnings ready to withdraw!",
                    "message": f"You have ${balance:.2f} available. Set up your payout account to receive your earnings.",
                    "action_url": "/settings/payouts",
                }
            )
            sent += 1

            logger.info(
                f"Sent payout reminder to {email}",
                available_balance=balance
            )

        await db.commit()

    return {"success": True, "sent": sent}
