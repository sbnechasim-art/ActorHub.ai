"""
Shared Database Connection Pool for Worker Tasks

This module provides a singleton database engine and session factory
to be shared across all Celery tasks, avoiding the overhead of creating
new connections for each task.
"""
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from config import settings

import structlog

logger = structlog.get_logger()

# Singleton engine and session factory
_engine: Optional[AsyncEngine] = None
_session_factory = None


def get_engine() -> AsyncEngine:
    """
    Get or create the shared database engine.

    Uses QueuePool for connection pooling in production,
    with reasonable defaults for worker tasks.
    """
    global _engine

    if _engine is None:
        # Convert sync URL to async URL if needed
        db_url = settings.DATABASE_URL
        if "postgresql://" in db_url and "+asyncpg" not in db_url:
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

        _engine = create_async_engine(
            db_url,
            # Pool configuration for worker tasks
            poolclass=QueuePool,
            pool_size=5,  # Base connections per worker
            max_overflow=10,  # Extra connections under load
            pool_timeout=30,  # Wait time for connection
            pool_recycle=1800,  # Recycle connections every 30 min
            pool_pre_ping=True,  # Verify connections before use
            echo=settings.DEBUG if hasattr(settings, 'DEBUG') else False,
        )

        logger.info("Worker database engine created", pool_size=5, max_overflow=10)

    return _engine


def get_session_factory():
    """Get or create the shared session factory."""
    global _session_factory

    if _session_factory is None:
        _session_factory = sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        logger.info("Worker session factory created")

    return _session_factory


@asynccontextmanager
async def get_db_session():
    """
    Get a database session from the shared pool.

    Usage:
        async with get_db_session() as db:
            result = await db.execute(query)
    """
    factory = get_session_factory()
    session = factory()

    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def close_engine():
    """Close the database engine and all connections."""
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Worker database engine closed")


def run_async(coro):
    """
    Run an async coroutine in a sync context.

    Creates a new event loop for each call to ensure
    clean async context in Celery tasks.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
