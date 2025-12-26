"""
Distributed Tracing with OpenTelemetry

Provides end-to-end request tracing across:
- FastAPI HTTP requests
- SQLAlchemy database queries
- Redis operations
- External HTTP calls (httpx)
- Celery background tasks

Trace data is exported to Jaeger or OTLP-compatible backends.
"""

import os
from typing import Optional
from contextlib import contextmanager

import structlog
from fastapi import FastAPI, Request

from app.core.config import settings

logger = structlog.get_logger()

# Global tracer instance
_tracer = None
_trace_provider = None


def get_tracer():
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None:
        try:
            from opentelemetry import trace
            _tracer = trace.get_tracer("actorhub.api", settings.VERSION)
        except ImportError:
            logger.warning("OpenTelemetry not installed, tracing disabled")
            _tracer = _NoOpTracer()
    return _tracer


class _NoOpTracer:
    """No-op tracer when OpenTelemetry is not installed."""

    def start_span(self, name, **kwargs):
        return _NoOpSpan()

    def start_as_current_span(self, name, **kwargs):
        return _NoOpSpanContext()


class _NoOpSpan:
    """No-op span."""

    def set_attribute(self, key, value):
        pass

    def set_status(self, status):
        pass

    def record_exception(self, exception):
        pass

    def end(self):
        pass


class _NoOpSpanContext:
    """No-op context manager for spans."""

    def __enter__(self):
        return _NoOpSpan()

    def __exit__(self, *args):
        pass


def setup_tracing(app: FastAPI) -> None:
    """
    Initialize OpenTelemetry tracing for the application.

    Configures:
    - Trace provider with batched span export
    - Auto-instrumentation for FastAPI, SQLAlchemy, Redis, httpx
    - Context propagation headers (W3C Trace Context)
    """
    global _trace_provider, _tracer

    # Check if tracing is enabled
    if not settings.ENABLE_TRACING:
        logger.info("Tracing disabled via configuration")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
        from opentelemetry.propagate import set_global_textmap
        from opentelemetry.propagators.composite import CompositePropagator
        from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
        from opentelemetry.baggage.propagation import W3CBaggagePropagator
    except ImportError:
        logger.warning(
            "OpenTelemetry packages not installed. Install with: "
            "pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi"
        )
        return

    # Create resource describing this service
    resource = Resource.create({
        SERVICE_NAME: "actorhub-api",
        SERVICE_VERSION: settings.VERSION,
        "deployment.environment": settings.ENVIRONMENT,
    })

    # Create trace provider
    _trace_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(_trace_provider)

    # Configure exporter based on settings
    _configure_exporter(_trace_provider)

    # Set up context propagation (W3C Trace Context + Baggage)
    set_global_textmap(CompositePropagator([
        TraceContextTextMapPropagator(),
        W3CBaggagePropagator(),
    ]))

    # Auto-instrument FastAPI
    _instrument_fastapi(app)

    # Auto-instrument other libraries
    _instrument_sqlalchemy()
    _instrument_redis()
    _instrument_httpx()

    # Get tracer instance
    _tracer = trace.get_tracer("actorhub.api", settings.VERSION)

    logger.info(
        "OpenTelemetry tracing initialized",
        exporter=settings.OTEL_EXPORTER_TYPE,
        service="actorhub-api",
        environment=settings.ENVIRONMENT,
    )


def _configure_exporter(provider) -> None:
    """Configure the span exporter based on settings."""
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    exporter_type = getattr(settings, 'OTEL_EXPORTER_TYPE', 'console')

    if exporter_type == "jaeger":
        try:
            from opentelemetry.exporter.jaeger.thrift import JaegerExporter

            exporter = JaegerExporter(
                agent_host_name=getattr(settings, 'JAEGER_HOST', 'localhost'),
                agent_port=getattr(settings, 'JAEGER_PORT', 6831),
            )
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info("Jaeger exporter configured")
        except ImportError:
            logger.warning("Jaeger exporter not installed, falling back to console")
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    elif exporter_type == "otlp":
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

            exporter = OTLPSpanExporter(
                endpoint=getattr(settings, 'OTEL_EXPORTER_OTLP_ENDPOINT', 'http://localhost:4317'),
            )
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info("OTLP exporter configured")
        except ImportError:
            logger.warning("OTLP exporter not installed, falling back to console")
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    elif exporter_type == "zipkin":
        try:
            from opentelemetry.exporter.zipkin.json import ZipkinExporter

            exporter = ZipkinExporter(
                endpoint=getattr(settings, 'ZIPKIN_ENDPOINT', 'http://localhost:9411/api/v2/spans'),
            )
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info("Zipkin exporter configured")
        except ImportError:
            logger.warning("Zipkin exporter not installed, falling back to console")
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    else:
        # Console exporter for development
        if settings.DEBUG:
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
            logger.info("Console span exporter configured (debug mode)")


def _instrument_fastapi(app: FastAPI) -> None:
    """Instrument FastAPI with OpenTelemetry."""
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls="health,ready,metrics",
            tracer_provider=_trace_provider,
        )
        logger.debug("FastAPI instrumented")
    except ImportError:
        logger.warning("FastAPI instrumentation not available")


def _instrument_sqlalchemy() -> None:
    """Instrument SQLAlchemy with OpenTelemetry."""
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        SQLAlchemyInstrumentor().instrument(
            tracer_provider=_trace_provider,
            enable_commenter=True,
        )
        logger.debug("SQLAlchemy instrumented")
    except ImportError:
        logger.warning("SQLAlchemy instrumentation not available")


def _instrument_redis() -> None:
    """Instrument Redis with OpenTelemetry."""
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        RedisInstrumentor().instrument(
            tracer_provider=_trace_provider,
        )
        logger.debug("Redis instrumented")
    except ImportError:
        logger.warning("Redis instrumentation not available")


def _instrument_httpx() -> None:
    """Instrument httpx with OpenTelemetry."""
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument(
            tracer_provider=_trace_provider,
        )
        logger.debug("httpx instrumented")
    except ImportError:
        logger.warning("httpx instrumentation not available")


def get_current_trace_id() -> Optional[str]:
    """Get the current trace ID for logging correlation."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            return format(span.get_span_context().trace_id, '032x')
    except ImportError:
        # OpenTelemetry not installed - expected in some environments
        pass
    except Exception as e:
        logger.debug(f"Failed to get trace ID: {e}")
    return None


def get_current_span_id() -> Optional[str]:
    """Get the current span ID."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            return format(span.get_span_context().span_id, '016x')
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Failed to get span ID: {e}")
    return None


def inject_trace_context(headers: dict) -> dict:
    """
    Inject trace context into headers for propagation.

    Use this when making outbound HTTP calls to propagate trace context.
    """
    try:
        from opentelemetry import propagate
        propagate.inject(headers)
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Failed to inject trace context: {e}")
    return headers


def extract_trace_context(headers: dict):
    """
    Extract trace context from incoming headers.

    Use this to continue a trace from an upstream service.
    """
    try:
        from opentelemetry import propagate
        return propagate.extract(headers)
    except ImportError:
        return None
    except Exception as e:
        logger.debug(f"Failed to extract trace context: {e}")
        return None


@contextmanager
def trace_span(name: str, attributes: dict = None):
    """
    Context manager for creating a traced span.

    Usage:
        with trace_span("process_payment", {"amount": 100}) as span:
            # do work
            span.set_attribute("result", "success")
    """
    tracer = get_tracer()

    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            try:
                from opentelemetry.trace import Status, StatusCode
                span.set_status(Status(StatusCode.ERROR, str(e)))
            except ImportError:
                pass
            raise


def add_span_attributes(**kwargs) -> None:
    """Add attributes to the current span."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span:
            for key, value in kwargs.items():
                span.set_attribute(key, value)
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Failed to add span attributes: {e}")


def record_exception(exception: Exception) -> None:
    """Record an exception on the current span."""
    try:
        from opentelemetry import trace
        from opentelemetry.trace import Status, StatusCode

        span = trace.get_current_span()
        if span:
            span.record_exception(exception)
            span.set_status(Status(StatusCode.ERROR, str(exception)))
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Failed to record exception on span: {e}")


# Celery task tracing helpers

def get_trace_headers() -> dict:
    """
    Get current trace context as headers for passing to Celery tasks.

    Usage in API endpoint:
        headers = get_trace_headers()
        train_actor_pack.delay(actor_pack_id, ..., trace_headers=headers)
    """
    headers = {}
    try:
        from opentelemetry import propagate
        propagate.inject(headers)
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Failed to get trace headers: {e}")
    return headers


def continue_trace_from_headers(headers: dict):
    """
    Continue a trace from headers passed to a Celery task.

    Usage in Celery task:
        @app.task
        def my_task(..., trace_headers=None):
            ctx = continue_trace_from_headers(trace_headers or {})
            with trace.use_context(ctx):
                # traced work here
    """
    try:
        from opentelemetry import propagate
        return propagate.extract(headers)
    except ImportError:
        return None
    except Exception as e:
        logger.debug(f"Failed to continue trace from headers: {e}")
        return None
