"""
Celery Application Configuration

Includes distributed tracing integration for end-to-end visibility
and Prometheus metrics for monitoring and alerting.
"""
import time
import structlog
from celery import Celery
from celery.signals import (
    task_prerun,
    task_postrun,
    task_failure,
    task_retry,
    worker_process_init,
    worker_ready,
    worker_shutting_down,
)

from config import settings

logger = structlog.get_logger()

# Task timing storage (thread-local would be better for production)
_task_start_times = {}

app = Celery(
    'actorhub_worker',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        'tasks.training',
        'tasks.face_recognition',
        'tasks.notifications',
        'tasks.cleanup',
        'tasks.payouts',
    ]
)


# =============================================================================
# Celery Signal Handlers for Tracing & Logging
# =============================================================================

@worker_process_init.connect
def init_worker_tracing(**kwargs):
    """Initialize tracing when worker process starts."""
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME

        resource = Resource.create({
            SERVICE_NAME: "actorhub-worker",
        })
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)
        logger.info("Worker tracing initialized")
    except ImportError:
        logger.info("OpenTelemetry not available, worker tracing disabled")


@worker_ready.connect
def init_worker_metrics(sender, **kwargs):
    """Initialize Prometheus metrics when worker is ready."""
    try:
        from metrics import start_metrics_server, init_worker_info
        import socket

        # Start metrics HTTP server on port 9090
        start_metrics_server(port=9090)

        # Record worker info
        hostname = socket.gethostname()
        concurrency = sender.concurrency if hasattr(sender, 'concurrency') else 1
        init_worker_info(hostname, concurrency)

        logger.info("Worker metrics initialized", hostname=hostname)
    except Exception as e:
        logger.warning(f"Failed to initialize metrics: {e}")


@worker_shutting_down.connect
def worker_shutdown_handler(**kwargs):
    """Log worker shutdown."""
    logger.info("Worker shutting down")


@task_prerun.connect
def task_prerun_handler(task_id, task, args, kwargs, **rest):
    """Log task start with correlation context and record metrics."""
    trace_headers = kwargs.get("trace_headers", {})
    correlation_id = None

    if trace_headers:
        # Extract correlation_id from trace headers
        traceparent = trace_headers.get("traceparent", "")
        if traceparent:
            parts = traceparent.split("-")
            if len(parts) >= 2:
                correlation_id = parts[1][:16]
        correlation_id = correlation_id or trace_headers.get("correlation_id")

    # Record start time for duration calculation
    _task_start_times[task_id] = time.time()

    # Record metrics
    try:
        from metrics import record_task_start
        queue = _get_queue_for_task(task.name)
        record_task_start(task.name, queue)
    except Exception as e:
        logger.debug(f"Failed to record task start metric: {e}")

    logger.bind(
        task_id=task_id,
        task_name=task.name,
        correlation_id=correlation_id or "no-correlation",
    ).info("Task starting")


@task_postrun.connect
def task_postrun_handler(task_id, task, args, kwargs, retval, state, **rest):
    """Log task completion and record metrics."""
    # Calculate duration
    start_time = _task_start_times.pop(task_id, None)
    duration = time.time() - start_time if start_time else 0

    # Record metrics
    try:
        from metrics import record_task_complete
        queue = _get_queue_for_task(task.name)
        status = 'success' if state == 'SUCCESS' else 'failure'
        record_task_complete(task.name, queue, status, duration)
    except Exception as e:
        logger.debug(f"Failed to record task complete metric: {e}")

    logger.bind(
        task_id=task_id,
        task_name=task.name,
        state=state,
        duration_seconds=round(duration, 3),
    ).info("Task completed")


@task_failure.connect
def task_failure_handler(task_id, exception, args, kwargs, traceback, einfo, sender=None, **rest):
    """Log task failure with full context and record metrics."""
    trace_headers = kwargs.get("trace_headers", {})
    correlation_id = trace_headers.get("correlation_id") if trace_headers else None
    error_type = type(exception).__name__

    # Record failure metric
    try:
        from metrics import record_task_failure
        task_name = sender.name if sender else 'unknown'
        queue = _get_queue_for_task(task_name)
        record_task_failure(task_name, queue, error_type)
    except Exception as e:
        logger.debug(f"Failed to record task failure metric: {e}")

    logger.bind(
        task_id=task_id,
        correlation_id=correlation_id or "no-correlation",
    ).error(
        "Task failed",
        error=str(exception),
        error_type=error_type,
    )


@task_retry.connect
def task_retry_handler(request, reason, einfo, **rest):
    """Log task retry and record metrics."""
    # Record retry metric
    try:
        from metrics import record_task_retry
        queue = _get_queue_for_task(request.task)
        record_task_retry(request.task, queue, str(reason)[:50])
    except Exception as e:
        logger.debug(f"Failed to record task retry metric: {e}")

    logger.bind(
        task_id=request.id,
        task_name=request.task,
        retry_count=request.retries,
    ).warning("Task retrying", reason=str(reason))


def _get_queue_for_task(task_name: str) -> str:
    """Get queue name for a task based on routing rules."""
    if 'training' in task_name:
        return 'training'
    elif 'face_recognition' in task_name:
        return 'face'
    elif 'notifications' in task_name:
        return 'notifications'
    elif 'cleanup' in task_name:
        return 'cleanup'
    elif 'payouts' in task_name:
        return 'payouts'
    return 'default'

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=86400,  # 24 hours
    broker_connection_retry_on_startup=True,
)

# Task routing
app.conf.task_routes = {
    'tasks.training.*': {'queue': 'training'},
    'tasks.face_recognition.*': {'queue': 'face'},
    'tasks.notifications.*': {'queue': 'notifications'},
    'tasks.cleanup.*': {'queue': 'cleanup'},
    'tasks.payouts.*': {'queue': 'payouts'},
}

# Periodic tasks
app.conf.beat_schedule = {
    'cleanup-expired-downloads': {
        'task': 'tasks.cleanup.cleanup_expired_downloads',
        'schedule': 3600.0,  # Every hour
    },
    'cleanup-orphan-files': {
        'task': 'tasks.cleanup.cleanup_orphan_files',
        'schedule': 86400.0,  # Every day
    },
    'update-usage-stats': {
        'task': 'tasks.cleanup.update_usage_stats',
        'schedule': 300.0,  # Every 5 minutes
    },
    # Payout tasks
    'mature-pending-earnings': {
        'task': 'tasks.payouts.mature_pending_earnings',
        'schedule': 3600.0,  # Every hour - check for matured earnings
    },
    'process-auto-payouts': {
        'task': 'tasks.payouts.process_auto_payouts',
        'schedule': 604800.0,  # Weekly (7 days) - automatic payouts
    },
    'send-payout-reminders': {
        'task': 'tasks.payouts.send_payout_reminders',
        'schedule': 604800.0,  # Weekly - remind creators to set up payouts
    },
}

if __name__ == '__main__':
    app.start()
