"""
Database Configuration
Async SQLAlchemy setup with PostgreSQL + pgvector

Features:
- Connection pooling with health checks
- Retry logic for transient failures
- Query timeout protection
- Proper error handling and rollback
"""

import asyncio
import time
from typing import AsyncGenerator

import structlog
from sqlalchemy import MetaData, event
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = structlog.get_logger()

# Retry configuration for transient database errors
DB_RETRY_ATTEMPTS = 3
DB_RETRY_DELAY = 0.5  # Base delay in seconds
DB_RETRYABLE_ERRORS = (
    OperationalError,
    InterfaceError,
    ConnectionRefusedError,
    TimeoutError,
)

# Naming convention for constraints
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for all models"""

    metadata = MetaData(naming_convention=naming_convention)


# Create async engine with optimized pool settings
engine = create_async_engine(
    settings.database_url_async,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verify connections before use
    pool_timeout=30,  # Wait up to 30 seconds for a connection
    pool_recycle=3600,  # Recycle connections after 1 hour (prevents stale connections)
    connect_args={
        "command_timeout": 60,  # Query timeout in seconds
    },
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database sessions with retry logic.

    Handles:
    - Automatic commit on success
    - Automatic rollback on exceptions
    - Proper connection cleanup
    - Timeout handling
    - Retry for transient connection errors
    """
    last_error = None

    for attempt in range(1, DB_RETRY_ATTEMPTS + 1):
        try:
            async with async_session_maker() as session:
                try:
                    yield session
                    await session.commit()
                    return  # Success, exit the retry loop
                except DB_RETRYABLE_ERRORS as e:
                    await session.rollback()
                    raise  # Re-raise to trigger retry
                except Exception as e:
                    await session.rollback()
                    logger.error(
                        "Database session error - rolled back",
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    raise
                finally:
                    await session.close()

        except DB_RETRYABLE_ERRORS as e:
            last_error = e
            if attempt < DB_RETRY_ATTEMPTS:
                delay = DB_RETRY_DELAY * (2 ** (attempt - 1))  # Exponential backoff
                logger.warning(
                    f"Database connection error, retrying in {delay}s",
                    attempt=attempt,
                    max_attempts=DB_RETRY_ATTEMPTS,
                    error=str(e),
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "Database connection failed after all retries",
                    attempts=DB_RETRY_ATTEMPTS,
                    error=str(e),
                )
                raise

    if last_error:
        raise last_error


async def get_db_no_retry() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session without retry logic.
    Use for operations where retry could cause issues (e.g., long transactions).
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(
                "Database session error - rolled back",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database - create tables"""
    async with engine.begin() as conn:
        # Import all models to register them
        from app.models import identity, marketplace, user  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connection"""
    await engine.dispose()
