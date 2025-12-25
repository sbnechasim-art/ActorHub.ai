"""
Prometheus Metrics for ActorHub Worker

Exposes metrics for task execution, retries, failures, and queue health.
"""
from prometheus_client import Counter, Histogram, Gauge, Info
import time
from functools import wraps
from typing import Callable
import structlog

logger = structlog.get_logger()

# ==============================================================================
# Task Execution Metrics
# ==============================================================================

TASK_STARTED = Counter(
    'celery_task_started_total',
    'Total number of tasks started',
    ['task_name', 'queue']
)

TASK_COMPLETED = Counter(
    'celery_task_completed_total',
    'Total number of tasks completed',
    ['task_name', 'queue', 'status']  # status: success, failure, retry
)

TASK_DURATION = Histogram(
    'celery_task_duration_seconds',
    'Task execution duration in seconds',
    ['task_name', 'queue'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0)
)

TASK_RETRIES = Counter(
    'celery_task_retries_total',
    'Total number of task retries',
    ['task_name', 'queue', 'reason']
)

TASK_FAILURES = Counter(
    'celery_task_failures_total',
    'Total number of task failures after max retries',
    ['task_name', 'queue', 'error_type']
)

# ==============================================================================
# Queue Metrics
# ==============================================================================

QUEUE_LENGTH = Gauge(
    'celery_queue_length',
    'Current number of messages in queue',
    ['queue']
)

ACTIVE_TASKS = Gauge(
    'celery_active_tasks',
    'Number of currently executing tasks',
    ['task_name', 'queue']
)

RESERVED_TASKS = Gauge(
    'celery_reserved_tasks',
    'Number of tasks reserved by workers',
    ['queue']
)

# ==============================================================================
# Training-Specific Metrics
# ==============================================================================

TRAINING_STARTED = Counter(
    'actor_pack_training_started_total',
    'Number of Actor Pack trainings started',
    ['quality_tier']  # standard, premium
)

TRAINING_COMPLETED = Counter(
    'actor_pack_training_completed_total',
    'Number of Actor Pack trainings completed',
    ['status', 'quality_tier']  # status: success, failed, cancelled
)

TRAINING_DURATION = Histogram(
    'actor_pack_training_duration_seconds',
    'Training duration in seconds',
    ['quality_tier'],
    buckets=(60, 120, 300, 600, 900, 1200, 1800, 2700, 3600)
)

TRAINING_QUALITY_SCORE = Histogram(
    'actor_pack_quality_score',
    'Quality scores of completed trainings',
    ['quality_tier'],
    buckets=(0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0)
)

ACTIVE_TRAININGS = Gauge(
    'actor_pack_trainings_active',
    'Number of currently active trainings'
)

# ==============================================================================
# Payout Metrics
# ==============================================================================

PAYOUTS_PROCESSED = Counter(
    'payouts_processed_total',
    'Number of payouts processed',
    ['status', 'type']  # status: success, failed; type: auto, manual
)

PAYOUT_AMOUNT = Histogram(
    'payout_amount_usd',
    'Payout amounts in USD',
    buckets=(10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000)
)

PAYOUT_FAILURES = Counter(
    'payout_failures_total',
    'Number of payout failures',
    ['error_type']  # stripe_error, insufficient_balance, etc.
)

# ==============================================================================
# Notification Metrics
# ==============================================================================

EMAILS_SENT = Counter(
    'emails_sent_total',
    'Number of emails sent',
    ['template', 'status']  # status: success, failed, bounced
)

EMAIL_DELIVERY_TIME = Histogram(
    'email_delivery_seconds',
    'Time to send email via SendGrid',
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0)
)

WEBHOOKS_SENT = Counter(
    'webhooks_sent_total',
    'Number of webhooks sent',
    ['status']  # success, failed
)

WEBHOOK_LATENCY = Histogram(
    'webhook_delivery_seconds',
    'Webhook delivery latency',
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
)

# ==============================================================================
# Face Recognition Metrics
# ==============================================================================

EMBEDDINGS_EXTRACTED = Counter(
    'face_embeddings_extracted_total',
    'Number of face embeddings extracted',
    ['status']  # success, no_face, error
)

EMBEDDING_EXTRACTION_TIME = Histogram(
    'face_embedding_extraction_seconds',
    'Time to extract face embedding',
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0)
)

VERIFICATIONS_PERFORMED = Counter(
    'face_verifications_total',
    'Number of face verifications performed',
    ['matched', 'threshold']  # matched: true/false
)

VERIFICATION_SCORE = Histogram(
    'face_verification_score',
    'Verification similarity scores',
    buckets=(0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0)
)

# ==============================================================================
# Distributed Locking Metrics
# ==============================================================================

LOCKS_ACQUIRED = Counter(
    'distributed_locks_acquired_total',
    'Number of distributed locks acquired',
    ['lock_name']
)

LOCKS_FAILED = Counter(
    'distributed_locks_failed_total',
    'Number of distributed lock acquisition failures',
    ['lock_name', 'reason']  # already_held, redis_error
)

LOCK_HOLD_TIME = Histogram(
    'distributed_lock_hold_seconds',
    'Time locks are held',
    ['lock_name'],
    buckets=(1, 5, 10, 30, 60, 300, 600, 1800, 3600)
)

# ==============================================================================
# Worker Info
# ==============================================================================

WORKER_INFO = Info(
    'celery_worker',
    'Celery worker information'
)


# ==============================================================================
# Metric Recording Helpers
# ==============================================================================

def record_task_start(task_name: str, queue: str = 'default'):
    """Record task start."""
    TASK_STARTED.labels(task_name=task_name, queue=queue).inc()
    ACTIVE_TASKS.labels(task_name=task_name, queue=queue).inc()


def record_task_complete(task_name: str, queue: str = 'default',
                        status: str = 'success', duration: float = 0):
    """Record task completion."""
    TASK_COMPLETED.labels(task_name=task_name, queue=queue, status=status).inc()
    TASK_DURATION.labels(task_name=task_name, queue=queue).observe(duration)
    ACTIVE_TASKS.labels(task_name=task_name, queue=queue).dec()


def record_task_retry(task_name: str, queue: str = 'default', reason: str = 'unknown'):
    """Record task retry."""
    TASK_RETRIES.labels(task_name=task_name, queue=queue, reason=reason).inc()


def record_task_failure(task_name: str, queue: str = 'default', error_type: str = 'unknown'):
    """Record task failure."""
    TASK_FAILURES.labels(task_name=task_name, queue=queue, error_type=error_type).inc()


def timed_task(task_name: str, queue: str = 'default'):
    """Decorator to time and record task metrics."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            record_task_start(task_name, queue)
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                record_task_complete(task_name, queue, 'success', duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                error_type = type(e).__name__
                record_task_complete(task_name, queue, 'failure', duration)
                record_task_failure(task_name, queue, error_type)
                raise
        return wrapper
    return decorator


# ==============================================================================
# Prometheus HTTP Server
# ==============================================================================

_metrics_server_started = False


def start_metrics_server(port: int = 9090):
    """Start Prometheus metrics HTTP server."""
    global _metrics_server_started
    if _metrics_server_started:
        return

    try:
        from prometheus_client import start_http_server
        start_http_server(port)
        _metrics_server_started = True
        logger.info(f"Prometheus metrics server started on port {port}")
    except Exception as e:
        logger.warning(f"Failed to start metrics server: {e}")


def init_worker_info(hostname: str, concurrency: int):
    """Initialize worker info metric."""
    WORKER_INFO.info({
        'hostname': hostname,
        'concurrency': str(concurrency),
        'version': '1.0.0',
    })
