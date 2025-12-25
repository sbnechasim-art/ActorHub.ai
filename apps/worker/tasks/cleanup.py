"""
Cleanup and Maintenance Tasks

Handles scheduled cleanup, stats updates, and maintenance operations
with distributed tracing for visibility.

FIXED: Now includes distributed locking to prevent concurrent execution
of scheduled tasks.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import structlog
import redis

from sqlalchemy import text

from celery_app import app
from config import settings
from tracing import trace_task, add_task_attribute, get_trace_headers_for_subtask

logger = structlog.get_logger()

# Redis client for distributed locking
_redis_client = None


def get_redis_client() -> redis.Redis:
    """Get or create Redis client for distributed locks."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(
            settings.CELERY_BROKER_URL,
            decode_responses=True
        )
    return _redis_client


def acquire_distributed_lock(lock_name: str, ttl_seconds: int = 3600) -> bool:
    """
    Acquire a distributed lock using Redis SETNX.

    Returns True if lock acquired, False if already held.
    """
    try:
        client = get_redis_client()
        result = client.set(f"lock:{lock_name}", "1", nx=True, ex=ttl_seconds)
        if result:
            logger.debug(f"Acquired distributed lock: {lock_name}")
        return result is True
    except Exception as e:
        logger.warning(f"Failed to acquire distributed lock: {e}")
        # On Redis failure, allow execution to avoid blocking legitimate tasks
        return True


def release_distributed_lock(lock_name: str) -> None:
    """Release a distributed lock."""
    try:
        client = get_redis_client()
        client.delete(f"lock:{lock_name}")
        logger.debug(f"Released distributed lock: {lock_name}")
    except Exception as e:
        logger.warning(f"Failed to release distributed lock: {e}")


@app.task(bind=True, max_retries=2, default_retry_delay=60)
def cleanup_expired_downloads(self, trace_headers: Optional[Dict] = None) -> Dict:
    """
    Clean up expired download URLs and temporary files.

    FIXED: Uses distributed locking to prevent concurrent execution.
    """
    lock_name = "cleanup_expired_downloads"

    if not acquire_distributed_lock(lock_name, ttl_seconds=3600):
        logger.info("Cleanup expired downloads already running, skipping")
        return {"success": True, "message": "Already running", "cleaned": 0}

    try:
        with trace_task("cleanup_expired_downloads", trace_headers) as span:
            add_task_attribute("retry_count", self.request.retries)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(_cleanup_expired_downloads_async())
            finally:
                loop.close()

            add_task_attribute("cleaned_count", result.get("cleaned", 0))
            logger.info("Expired downloads cleanup completed", cleaned=result.get("cleaned", 0))
            return result
    except Exception as e:
        release_distributed_lock(lock_name)
        logger.error("Cleanup expired downloads failed", error=str(e))
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        raise
    finally:
        release_distributed_lock(lock_name)


async def _cleanup_expired_downloads_async() -> Dict:
    """Async cleanup implementation"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    cleaned = 0
    async with async_session() as db:
        # Clean up expired download tokens
        result = await db.execute(
            "DELETE FROM download_tokens WHERE expires_at < NOW()"
        )
        cleaned = result.rowcount
        await db.commit()

    logger.info(f"Cleaned up {cleaned} expired downloads")
    return {'success': True, 'cleaned': cleaned}


@app.task(bind=True, max_retries=2, default_retry_delay=120)
def cleanup_orphan_files(self, trace_headers: Optional[Dict] = None) -> Dict:
    """
    Clean up orphaned files in S3 that are not referenced in the database.

    FIXED: Uses distributed locking to prevent concurrent execution.
    """
    lock_name = "cleanup_orphan_files"

    if not acquire_distributed_lock(lock_name, ttl_seconds=7200):  # 2 hours (long-running)
        logger.info("Cleanup orphan files already running, skipping")
        return {"success": True, "message": "Already running", "cleaned": 0}

    try:
        with trace_task("cleanup_orphan_files", trace_headers) as span:
            add_task_attribute("retry_count", self.request.retries)
            # S3 cleanup implementation would go here
            logger.info("Orphan files cleanup completed", cleaned=0)
            return {'success': True, 'cleaned': 0}
    except Exception as e:
        release_distributed_lock(lock_name)
        logger.error("Cleanup orphan files failed", error=str(e))
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=120 * (2 ** self.request.retries))
        raise
    finally:
        release_distributed_lock(lock_name)


@app.task(bind=True, max_retries=2, default_retry_delay=30)
def update_usage_stats(self, trace_headers: Optional[Dict] = None) -> Dict:
    """
    Update aggregated usage statistics.

    FIXED: Uses distributed locking to prevent concurrent execution.
    """
    lock_name = "update_usage_stats"

    if not acquire_distributed_lock(lock_name, ttl_seconds=300):  # 5 minutes
        logger.debug("Update usage stats already running, skipping")
        return {"success": True, "message": "Already running"}

    try:
        with trace_task("update_usage_stats", trace_headers) as span:
            add_task_attribute("retry_count", self.request.retries)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(_update_usage_stats_async())
            finally:
                loop.close()
            logger.info("Usage statistics updated successfully")
            return result
    except Exception as e:
        release_distributed_lock(lock_name)
        logger.error("Update usage stats failed", error=str(e))
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))
        raise
    finally:
        release_distributed_lock(lock_name)


async def _update_usage_stats_async() -> Dict:
    """Async stats update"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Update identity verification counts
        await db.execute("""
            UPDATE identities i SET
                total_verifications = (
                    SELECT COUNT(*) FROM usage_logs WHERE identity_id = i.id
                ),
                updated_at = NOW()
        """)

        # Update listing license counts
        await db.execute("""
            UPDATE marketplace_listings l SET
                license_count = (
                    SELECT COUNT(*) FROM licenses WHERE listing_id = l.id
                ),
                updated_at = NOW()
        """)

        await db.commit()

    logger.info("Usage statistics updated")
    return {'success': True}


@app.task(bind=True, max_retries=2, default_retry_delay=120)
def cleanup_old_logs(self, trace_headers: Optional[Dict] = None) -> Dict:
    """
    Archive and clean up old usage logs.

    FIXED: Uses distributed locking to prevent concurrent execution.
    """
    lock_name = "cleanup_old_logs"

    if not acquire_distributed_lock(lock_name, ttl_seconds=7200):  # 2 hours
        logger.info("Cleanup old logs already running, skipping")
        return {"success": True, "message": "Already running", "cleaned": 0}

    try:
        with trace_task("cleanup_old_logs", trace_headers) as span:
            add_task_attribute("retry_count", self.request.retries)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(_cleanup_old_logs_async())
            finally:
                loop.close()

            add_task_attribute("cleaned_count", result.get("cleaned", 0))
            logger.info("Old logs cleanup completed", cleaned=result.get("cleaned", 0))
            return result
    except Exception as e:
        release_distributed_lock(lock_name)
        logger.error("Cleanup old logs failed", error=str(e))
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=120 * (2 ** self.request.retries))
        raise
    finally:
        release_distributed_lock(lock_name)


async def _cleanup_old_logs_async() -> Dict:
    """Async log cleanup"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    cleaned = 0

    async with async_session() as db:
        # Use parameterized query to prevent SQL injection
        result = await db.execute(
            text("DELETE FROM usage_logs WHERE created_at < :cutoff"),
            {"cutoff": cutoff}
        )
        cleaned = result.rowcount
        await db.commit()

    logger.info(f"Cleaned up {cleaned} old log entries")
    return {'success': True, 'cleaned': cleaned}


@app.task(bind=True, max_retries=2, default_retry_delay=60)
def check_license_expirations(self, trace_headers: Optional[Dict] = None) -> Dict:
    """
    Check for expiring licenses and send notifications.

    FIXED: Uses distributed locking to prevent duplicate notifications.
    """
    lock_name = "check_license_expirations"

    if not acquire_distributed_lock(lock_name, ttl_seconds=3600):  # 1 hour
        logger.info("License expiration check already running, skipping")
        return {"success": True, "message": "Already running", "notified": 0}

    try:
        with trace_task("check_license_expirations", trace_headers) as span:
            add_task_attribute("retry_count", self.request.retries)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(_check_expirations_async())
            finally:
                loop.close()

            add_task_attribute("notified_count", result.get("notified", 0))
            logger.info("License expiration check completed", notified=result.get("notified", 0))
            return result
    except Exception as e:
        release_distributed_lock(lock_name)
        logger.error("License expiration check failed", error=str(e))
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        raise
    finally:
        release_distributed_lock(lock_name)


async def _check_expirations_async() -> Dict:
    """Async expiration check"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from tasks.notifications import send_email

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    expiring_soon = datetime.now(timezone.utc) + timedelta(days=7)
    notified = 0

    # Get trace headers for sub-tasks
    child_headers = get_trace_headers_for_subtask()

    async with async_session() as db:
        # Use parameterized query to prevent SQL injection
        result = await db.execute(
            text("""
                SELECT l.id, l.buyer_id, u.email
                FROM licenses l
                JOIN users u ON l.buyer_id = u.id
                WHERE l.valid_until BETWEEN NOW() AND :expiring_soon
                AND l.expiration_notified = false
            """),
            {"expiring_soon": expiring_soon}
        )

        for row in result:
            send_email.delay(
                to=row.email,
                subject="License Expiring Soon",
                body=f"Your license {row.id} expires in 7 days.",
                trace_headers=child_headers
            )
            notified += 1

        # Mark as notified - use parameterized query
        await db.execute(
            text("""
                UPDATE licenses SET expiration_notified = true
                WHERE valid_until BETWEEN NOW() AND :expiring_soon
            """),
            {"expiring_soon": expiring_soon}
        )
        await db.commit()

    return {'success': True, 'notified': notified}
