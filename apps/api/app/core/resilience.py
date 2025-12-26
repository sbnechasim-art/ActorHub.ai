"""
Resilience Framework
Circuit breakers, retry logic, and timeout handling for external services.

Provides enterprise-grade resilience patterns:
- Circuit breaker to prevent cascading failures
- Exponential backoff retry for transient failures
- Configurable timeouts per service
- Prometheus metrics for observability
"""

import asyncio
import functools
import re
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, Set, Type, TypeVar, Union

import structlog

logger = structlog.get_logger()

T = TypeVar("T")


# HIGH FIX: Log injection protection - sanitize log messages
def sanitize_log_message(message: str, max_length: int = 500) -> str:
    """
    Sanitize a message for safe logging.

    Prevents log injection attacks by:
    - Removing newlines and carriage returns (prevents fake log entries)
    - Limiting length to prevent log flooding
    - Removing control characters
    """
    if not isinstance(message, str):
        message = str(message)

    # Remove newlines, carriage returns, and other control characters
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', message)

    # Truncate to max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "...[truncated]"

    return sanitized


# ===========================================
# Prometheus Metrics (imported from monitoring)
# ===========================================
# Import centralized metrics to avoid duplication
from app.core.monitoring import (
    CIRCUIT_BREAKER_STATE,
    CIRCUIT_BREAKER_FAILURES,
    CIRCUIT_BREAKER_SUCCESSES,
    CIRCUIT_BREAKER_REJECTIONS,
    RETRY_ATTEMPTS,
    RETRY_SUCCESSES,
    RETRY_EXHAUSTED,
    OPERATION_TIMEOUTS,
    EXTERNAL_SERVICE_LATENCY,
    EXTERNAL_SERVICE_CALLS,
    EXTERNAL_CALL_DURATION,  # CRITICAL FIX: Export for payments.py
)


# ===========================================
# Circuit Breaker
# ===========================================


class CircuitState(Enum):
    CLOSED = 0  # Normal operation
    OPEN = 1  # Failing, reject calls
    HALF_OPEN = 2  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""

    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes in half-open to close
    timeout: float = 60.0  # Seconds before trying half-open
    excluded_exceptions: Set[Type[Exception]] = field(default_factory=set)


class CircuitBreaker:
    """
    Circuit breaker implementation for external services.

    States:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Service failing, calls rejected immediately
    - HALF_OPEN: Testing recovery, limited calls allowed
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()  # For async methods
        self._thread_lock = threading.Lock()  # For sync methods (thread pool safety)

        # Set initial metric
        CIRCUIT_BREAKER_STATE.labels(service=name).set(0)

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def is_closed(self) -> bool:
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        return self._state == CircuitState.OPEN

    async def _check_state(self) -> bool:
        """Check if call should be allowed. Returns True if allowed."""
        async with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                # Check if timeout has passed
                if self._last_failure_time:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed >= self.config.timeout:
                        self._state = CircuitState.HALF_OPEN
                        self._success_count = 0
                        CIRCUIT_BREAKER_STATE.labels(service=self.name).set(2)
                        logger.info(
                            f"Circuit breaker {self.name} entering half-open state"
                        )
                        return True
                # Increment rejection counter
                CIRCUIT_BREAKER_REJECTIONS.labels(service=self.name).inc()
                return False

            # HALF_OPEN - allow calls
            return True

    async def _record_success(self):
        """Record a successful call"""
        async with self._lock:
            CIRCUIT_BREAKER_SUCCESSES.labels(service=self.name).inc()

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    CIRCUIT_BREAKER_STATE.labels(service=self.name).set(0)
                    logger.info(f"Circuit breaker {self.name} closed (recovered)")

            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0

    async def _record_failure(self, exception: Exception):
        """Record a failed call"""
        async with self._lock:
            # Check if exception should be excluded
            if type(exception) in self.config.excluded_exceptions:
                return

            CIRCUIT_BREAKER_FAILURES.labels(service=self.name).inc()
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                # Immediate open on failure in half-open
                self._state = CircuitState.OPEN
                CIRCUIT_BREAKER_STATE.labels(service=self.name).set(1)
                logger.warning(
                    f"Circuit breaker {self.name} opened (failed in half-open)"
                )

            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    self._state = CircuitState.OPEN
                    CIRCUIT_BREAKER_STATE.labels(service=self.name).set(1)
                    logger.warning(
                        f"Circuit breaker {self.name} opened after {self._failure_count} failures"
                    )

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute a call through the circuit breaker"""
        if not await self._check_state():
            raise CircuitBreakerOpenError(
                f"Circuit breaker {self.name} is open. Service unavailable."
            )

        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure(e)
            raise

    # Sync methods for use in thread pools (thread-safe with threading.Lock)
    def can_execute(self) -> bool:
        """Sync check if circuit allows execution (for use in thread pools)"""
        with self._thread_lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                if self._last_failure_time:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed >= self.config.timeout:
                        self._state = CircuitState.HALF_OPEN
                        self._success_count = 0
                        CIRCUIT_BREAKER_STATE.labels(service=self.name).set(2)
                        logger.info(f"Circuit breaker {self.name} entering half-open state")
                        return True
                CIRCUIT_BREAKER_REJECTIONS.labels(service=self.name).inc()
                return False

            return True  # HALF_OPEN

    def record_success(self):
        """Sync record success (for use in thread pools)"""
        with self._thread_lock:
            CIRCUIT_BREAKER_SUCCESSES.labels(service=self.name).inc()

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    CIRCUIT_BREAKER_STATE.labels(service=self.name).set(0)
                    logger.info(f"Circuit breaker {self.name} closed (recovered)")

            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    def record_failure(self, exception: Optional[Exception] = None):
        """Sync record failure (for use in thread pools)"""
        with self._thread_lock:
            if exception and type(exception) in self.config.excluded_exceptions:
                return

            CIRCUIT_BREAKER_FAILURES.labels(service=self.name).inc()
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                CIRCUIT_BREAKER_STATE.labels(service=self.name).set(1)
                logger.warning(f"Circuit breaker {self.name} opened (failed in half-open)")

            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    self._state = CircuitState.OPEN
                    CIRCUIT_BREAKER_STATE.labels(service=self.name).set(1)
                    logger.warning(
                        f"Circuit breaker {self.name} opened after {self._failure_count} failures"
                    )


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""

    pass


# ===========================================
# Retry Logic
# ===========================================


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""

    max_attempts: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 30.0  # Maximum delay between retries
    exponential_base: float = 2.0  # Exponential backoff base
    jitter: bool = True  # Add randomness to prevent thundering herd
    retryable_exceptions: Set[Type[Exception]] = field(
        default_factory=lambda: {
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
        }
    )


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay for retry attempt with exponential backoff"""
    import random

    delay = config.base_delay * (config.exponential_base ** (attempt - 1))
    delay = min(delay, config.max_delay)

    if config.jitter:
        # Add up to 25% jitter
        delay = delay * (0.75 + random.random() * 0.5)

    return delay


async def retry_async(
    func: Callable[..., T],
    *args,
    config: Optional[RetryConfig] = None,
    service_name: str = "unknown",
    operation: str = "call",
    **kwargs,
) -> T:
    """
    Execute an async function with retry logic.

    Uses exponential backoff with jitter to prevent thundering herd.
    """
    config = config or RetryConfig()
    last_exception: Optional[Exception] = None

    for attempt in range(1, config.max_attempts + 1):
        try:
            if attempt > 1:
                # Track retry attempts (not the first attempt)
                RETRY_ATTEMPTS.labels(service=service_name, operation=operation).inc()

            result = await func(*args, **kwargs)

            # If succeeded after retries, track it
            if attempt > 1:
                RETRY_SUCCESSES.labels(service=service_name, operation=operation).inc()

            return result

        except Exception as e:
            last_exception = e

            # Check if exception is retryable
            is_retryable = any(
                isinstance(e, exc_type) for exc_type in config.retryable_exceptions
            )

            if not is_retryable or attempt == config.max_attempts:
                if attempt == config.max_attempts and is_retryable:
                    RETRY_EXHAUSTED.labels(service=service_name, operation=operation).inc()

                # HIGH FIX: Sanitize error message to prevent log injection
                logger.error(
                    f"Retry failed for {service_name}",
                    attempt=attempt,
                    max_attempts=config.max_attempts,
                    error=sanitize_log_message(str(e)),
                    retryable=is_retryable,
                )
                raise

            delay = calculate_delay(attempt, config)
            # HIGH FIX: Sanitize error message to prevent log injection
            logger.warning(
                f"Retry attempt {attempt}/{config.max_attempts} for {service_name}",
                delay=delay,
                error=sanitize_log_message(str(e)),
            )
            await asyncio.sleep(delay)

    raise last_exception  # Should never reach here


def retry_sync(
    func: Callable[..., T],
    *args,
    config: Optional[RetryConfig] = None,
    service_name: str = "unknown",
    operation: str = "call",
    **kwargs,
) -> T:
    """Execute a sync function with retry logic"""
    config = config or RetryConfig()
    last_exception: Optional[Exception] = None

    for attempt in range(1, config.max_attempts + 1):
        try:
            if attempt > 1:
                RETRY_ATTEMPTS.labels(service=service_name, operation=operation).inc()

            result = func(*args, **kwargs)

            if attempt > 1:
                RETRY_SUCCESSES.labels(service=service_name, operation=operation).inc()

            return result

        except Exception as e:
            last_exception = e

            is_retryable = any(
                isinstance(e, exc_type) for exc_type in config.retryable_exceptions
            )

            if not is_retryable or attempt == config.max_attempts:
                if attempt == config.max_attempts and is_retryable:
                    RETRY_EXHAUSTED.labels(service=service_name, operation=operation).inc()
                raise

            delay = calculate_delay(attempt, config)
            # HIGH FIX: Sanitize error message to prevent log injection
            logger.warning(
                f"Retry attempt {attempt}/{config.max_attempts} for {service_name}",
                delay=delay,
                error=sanitize_log_message(str(e)),
            )
            time.sleep(delay)

    raise last_exception


# ===========================================
# Timeout Wrapper
# ===========================================


async def with_timeout(
    func: Callable[..., T],
    *args,
    timeout: float,
    service_name: str = "unknown",
    operation: str = "call",
    **kwargs,
) -> T:
    """
    Execute an async function with timeout.

    Args:
        func: Async function to execute
        timeout: Timeout in seconds
        service_name: Name for metrics/logging
        operation: Operation name for metrics
    """
    start_time = time.time()

    try:
        result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
        duration = time.time() - start_time
        EXTERNAL_SERVICE_LATENCY.labels(service=service_name, operation=operation).observe(
            duration
        )
        EXTERNAL_SERVICE_CALLS.labels(
            service=service_name, operation=operation, status="success"
        ).inc()
        return result

    except asyncio.TimeoutError:
        duration = time.time() - start_time
        EXTERNAL_SERVICE_LATENCY.labels(service=service_name, operation=operation).observe(
            duration
        )
        OPERATION_TIMEOUTS.labels(service=service_name, operation=operation).inc()
        EXTERNAL_SERVICE_CALLS.labels(
            service=service_name, operation=operation, status="timeout"
        ).inc()
        logger.error(
            f"Timeout calling {service_name}.{operation}",
            timeout=timeout,
            duration=duration,
        )
        raise TimeoutError(f"{service_name}.{operation} timed out after {timeout}s")


# ===========================================
# Resilient Service Wrapper
# ===========================================


class ResilientService:
    """
    Base class for resilient external service clients.

    Provides:
    - Circuit breaker protection
    - Retry with exponential backoff
    - Configurable timeouts
    - Metrics collection
    """

    def __init__(
        self,
        service_name: str,
        circuit_config: Optional[CircuitBreakerConfig] = None,
        retry_config: Optional[RetryConfig] = None,
        default_timeout: float = 30.0,
    ):
        self.service_name = service_name
        self.circuit_breaker = CircuitBreaker(service_name, circuit_config)
        self.retry_config = retry_config or RetryConfig()
        self.default_timeout = default_timeout

    async def execute(
        self,
        func: Callable[..., T],
        *args,
        operation: str = "call",
        timeout: Optional[float] = None,
        skip_retry: bool = False,
        **kwargs,
    ) -> T:
        """
        Execute a call with full resilience stack:
        1. Circuit breaker check
        2. Timeout wrapper
        3. Retry logic
        """
        timeout = timeout or self.default_timeout

        async def wrapped_call():
            return await with_timeout(
                func,
                *args,
                timeout=timeout,
                service_name=self.service_name,
                operation=operation,
                **kwargs,
            )

        # Apply circuit breaker
        async def circuit_wrapped():
            return await self.circuit_breaker.call(wrapped_call)

        # Apply retry if not skipped
        if skip_retry:
            return await circuit_wrapped()

        return await retry_async(
            circuit_wrapped,
            config=self.retry_config,
            service_name=self.service_name,
        )


# ===========================================
# Service-Specific Configurations
# ===========================================

# Stripe - Payment critical, moderate retry
STRIPE_CIRCUIT_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    success_threshold=2,
    timeout=60.0,
)

STRIPE_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=10.0,
    retryable_exceptions={
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
    },
)

# Database - Critical, fast retry
DATABASE_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=0.5,
    max_delay=5.0,
    retryable_exceptions={
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
    },
)

# External APIs - Moderate tolerance
EXTERNAL_API_CIRCUIT_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    success_threshold=3,
    timeout=120.0,
)

EXTERNAL_API_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=2.0,
    max_delay=30.0,
)

# Storage - More tolerance for slow uploads
STORAGE_CIRCUIT_CONFIG = CircuitBreakerConfig(
    failure_threshold=10,
    success_threshold=2,
    timeout=300.0,
)

STORAGE_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=15.0,
)


# ===========================================
# Decorators
# ===========================================


def resilient(
    service_name: str,
    timeout: float = 30.0,
    circuit_config: Optional[CircuitBreakerConfig] = None,
    retry_config: Optional[RetryConfig] = None,
):
    """
    Decorator to add resilience to an async function.

    Usage:
        @resilient("stripe", timeout=30.0)
        async def create_customer(email: str):
            ...
    """
    circuit_breaker = CircuitBreaker(service_name, circuit_config)
    retry_cfg = retry_config or RetryConfig()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            async def call_with_timeout():
                return await with_timeout(
                    func,
                    *args,
                    timeout=timeout,
                    service_name=service_name,
                    operation=func.__name__,
                    **kwargs,
                )

            async def circuit_wrapped():
                return await circuit_breaker.call(call_with_timeout)

            return await retry_async(
                circuit_wrapped,
                config=retry_cfg,
                service_name=service_name,
            )

        return wrapper

    return decorator


# ===========================================
# Health Check Helper
# ===========================================


async def check_service_health(
    service_name: str,
    check_func: Callable[..., bool],
    timeout: float = 5.0,
) -> Dict[str, Any]:
    """
    Check health of an external service with timeout.

    Returns dict with status, latency, and error (if any).
    """
    start_time = time.time()

    try:
        result = await asyncio.wait_for(check_func(), timeout=timeout)
        latency = time.time() - start_time

        return {
            "service": service_name,
            "status": "healthy" if result else "degraded",
            "latency_ms": round(latency * 1000, 2),
        }

    except asyncio.TimeoutError:
        return {
            "service": service_name,
            "status": "timeout",
            "latency_ms": round(timeout * 1000, 2),
            "error": f"Health check timed out after {timeout}s",
        }

    except Exception as e:
        latency = time.time() - start_time
        return {
            "service": service_name,
            "status": "unhealthy",
            "latency_ms": round(latency * 1000, 2),
            # HIGH FIX: Sanitize error message to prevent log/response injection
            "error": sanitize_log_message(str(e), max_length=200),
        }
