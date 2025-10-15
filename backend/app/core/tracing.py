"""OpenTelemetry distributed tracing configuration."""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from backend.app.core.config import settings


def setup_tracing(app) -> None:
    """Configure OpenTelemetry tracing for the application."""

    if not settings.OTEL_ENABLED:
        return

    resource = Resource.create(
        {
            "service.name": settings.OTEL_SERVICE_NAME,
            "service.version": settings.VERSION,
            "deployment.environment": settings.ENVIRONMENT,
        }
    )

    provider = TracerProvider(resource=resource)

    if settings.OTEL_EXPORTER_ENDPOINT:
        # Production: send to OTLP collector
        otlp_exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_ENDPOINT)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    else:
        # Development: console output
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))

    trace.set_tracer_provider(provider)

    # Instrument FastAPI automatically
    FastAPIInstrumentor.instrument_app(app)
