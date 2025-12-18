"""
Cleanup and Maintenance Tasks
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict
import structlog

from celery_app import app
from config import settings

logger = structlog.get_logger()


@app.task
def cleanup_expired_downloads() -> Dict:
    """
    Clean up expired download URLs and temporary files.
    """
    logger.info("Running expired downloads cleanup")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(_cleanup_expired_downloads_async())


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


@app.task
def cleanup_orphan_files() -> Dict:
    """
    Clean up orphaned files in S3 that are not referenced in the database.
    """
    logger.info("Running orphan files cleanup")

    # S3 cleanup implementation would go here
    return {'success': True, 'cleaned': 0}


@app.task
def update_usage_stats() -> Dict:
    """
    Update aggregated usage statistics.
    """
    logger.info("Updating usage statistics")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(_update_usage_stats_async())


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


@app.task
def cleanup_old_logs() -> Dict:
    """
    Archive and clean up old usage logs.
    """
    logger.info("Cleaning up old logs")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(_cleanup_old_logs_async())


async def _cleanup_old_logs_async() -> Dict:
    """Async log cleanup"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    cutoff = datetime.utcnow() - timedelta(days=90)
    cleaned = 0

    async with async_session() as db:
        result = await db.execute(
            f"DELETE FROM usage_logs WHERE created_at < '{cutoff.isoformat()}'"
        )
        cleaned = result.rowcount
        await db.commit()

    logger.info(f"Cleaned up {cleaned} old log entries")
    return {'success': True, 'cleaned': cleaned}


@app.task
def check_license_expirations() -> Dict:
    """
    Check for expiring licenses and send notifications.
    """
    logger.info("Checking license expirations")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(_check_expirations_async())


async def _check_expirations_async() -> Dict:
    """Async expiration check"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from tasks.notifications import send_email

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    expiring_soon = datetime.utcnow() + timedelta(days=7)
    notified = 0

    async with async_session() as db:
        result = await db.execute(f"""
            SELECT l.id, l.buyer_id, u.email
            FROM licenses l
            JOIN users u ON l.buyer_id = u.id
            WHERE l.valid_until BETWEEN NOW() AND '{expiring_soon.isoformat()}'
            AND l.expiration_notified = false
        """)

        for row in result:
            send_email.delay(
                to=row.email,
                subject="License Expiring Soon",
                body=f"Your license {row.id} expires in 7 days."
            )
            notified += 1

        # Mark as notified
        await db.execute(f"""
            UPDATE licenses SET expiration_notified = true
            WHERE valid_until BETWEEN NOW() AND '{expiring_soon.isoformat()}'
        """)
        await db.commit()

    logger.info(f"Sent {notified} expiration notifications")
    return {'success': True, 'notified': notified}
