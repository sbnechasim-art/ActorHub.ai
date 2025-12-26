"""
Distributed Tracing for Celery Workers

Provides trace context propagation from API to workers,
ensuring end-to-end visibility across async task execution.
"""

import uuid
from typing import Dict, Optional
from contextlib import contextmanager
from functools import wraps

import structlog

logger = structlog.get_logger()

# Try to import OpenTelemetry, fallback to no-op if not available
try:
    from opentelemetry import trace, propagate
    from opentelemetry.trace import Status, StatusCode
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logger.warning("OpenTelemetry not installed, worker tracing disabled")


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for request tracking."""
    return str(uuid.uuid4())


def extract_correlation_id(trace_headers: Optional[Dict] = None) -> str:
    """
    Extract correlation ID from trace headers or generate a new one.

    The correlation ID is used to link all logs and spans for a single
    operation, even across service boundaries.
    """
    if trace_headers:
        # Try to get from W3C traceparent header
        traceparent = trace_headers.get("traceparent", "")
        if traceparent:
            # Extract trace-id from traceparent (format: version-traceid-parentid-flags)
            parts = traceparent.split("-")
            if len(parts) >= 2:
                return parts[1][:16]  # Use first 16 chars of trace-id

        # Try explicit correlation_id
        if "correlation_id" in trace_headers:
            return trace_headers["correlation_id"]

    return generate_correlation_id()


@contextmanager
def trace_task(
    task_name: str,
    trace_headers: Optional[Dict] = None,
    attributes: Optional[Dict] = None
):
    """
    Context manager for tracing Celery task execution.

    Usage:
        @app.task
        def my_task(arg1, trace_headers=None):
            with trace_task("my_task", trace_headers, {"arg1": arg1}) as span:
                # Task logic here
                span.set_attribute("result", "success")
    """
    correlation_id = extract_correlation_id(trace_headers)

    # Bind correlation_id to structlog for all subsequent logs
    bound_logger = logger.bind(
        correlation_id=correlation_id,
        task_name=task_name
    )

    if OTEL_AVAILABLE:
        # Extract parent context from headers
        ctx = None
        if trace_headers:
            ctx = propagate.extract(trace_headers)

        tracer = trace.get_tracer("actorhub.worker")

        with tracer.start_as_current_span(
            f"celery.task.{task_name}",
            context=ctx,
            kind=trace.SpanKind.CONSUMER
        ) as span:
            # Set standard attributes
            span.set_attribute("messaging.system", "celery")
            span.set_attribute("messaging.destination", task_name)
            span.set_attribute("correlation_id", correlation_id)

            if attributes:
                for key, value in attributes.items():
                    if value is not None:
                        span.set_attribute(key, str(value)[:256])  # Truncate long values

            try:
                bound_logger.info(
                    "Task started",
                    trace_id=format(span.get_span_context().trace_id, '032x')
                )
                yield span
                span.set_status(Status(StatusCode.OK))
                bound_logger.info("Task completed successfully")
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                bound_logger.error("Task failed", error=str(e))
                raise
    else:
        # No-op span for when OpenTelemetry isn't available
        class NoOpSpan:
            def set_attribute(self, key, value):
                pass
            def set_status(self, status):
                pass
            def record_exception(self, exc):
                pass

        try:
            bound_logger.info("Task started")
            yield NoOpSpan()
            bound_logger.info("Task completed successfully")
        except Exception as e:
            bound_logger.error("Task failed", error=str(e))
            raise


def traced_task(task_name: str = None, capture_args: bool = True):
    """
    Decorator for adding tracing to Celery tasks.

    Usage:
        @app.task
        @traced_task()
        def my_task(arg1, trace_headers=None):
            # Task logic
            pass

    Args:
        task_name: Override the task name for tracing (defaults to function name)
        capture_args: Whether to capture task arguments as span attributes
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = task_name or func.__name__
            trace_headers = kwargs.pop("trace_headers", None)

            # Capture args as attributes
            attributes = {}
            if capture_args:
                # Get function argument names
                import inspect
                sig = inspect.signature(func)
                param_names = list(sig.parameters.keys())

                # Map positional args to names
                for i, arg in enumerate(args):
                    if i < len(param_names):
                        param_name = param_names[i]
                        # Skip 'self' for bound methods
                        if param_name != "self":
                            attributes[param_name] = str(arg)[:256]

                # Add keyword args (excluding internal ones)
                for key, value in kwargs.items():
                    if not key.startswith("_"):
                        attributes[key] = str(value)[:256]

            with trace_task(name, trace_headers, attributes):
                return func(*args, **kwargs)

        return wrapper
    return decorator


def get_trace_headers_for_subtask() -> Dict:
    """
    Get trace headers to pass to sub-tasks for context propagation.

    Use this when one Celery task spawns another to maintain trace context.

    Usage:
        @app.task
        def parent_task(trace_headers=None):
            with trace_task("parent_task", trace_headers):
                # Get headers for child task
                child_headers = get_trace_headers_for_subtask()
                child_task.delay(..., trace_headers=child_headers)
    """
    headers = {}

    if OTEL_AVAILABLE:
        try:
            propagate.inject(headers)
        except Exception:
            pass

    # Also add correlation_id if we're in a bound context
    try:
        from structlog._config import _CONTEXT
        context = _CONTEXT.get({})
        if "correlation_id" in context:
            headers["correlation_id"] = context["correlation_id"]
    except Exception:
        pass

    return headers


def add_task_attribute(key: str, value) -> None:
    """Add an attribute to the current task span."""
    if OTEL_AVAILABLE:
        try:
            span = trace.get_current_span()
            if span:
                span.set_attribute(key, str(value)[:256])
        except Exception:
            pass


def record_task_exception(exception: Exception) -> None:
    """Record an exception on the current task span."""
    if OTEL_AVAILABLE:
        try:
            span = trace.get_current_span()
            if span:
                span.record_exception(exception)
                span.set_status(Status(StatusCode.ERROR, str(exception)))
        except Exception:
            pass
