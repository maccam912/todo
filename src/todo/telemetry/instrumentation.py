"""OpenTelemetry instrumentation setup."""

import logging
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.semconv.resource import ResourceAttributes

from todo.config import Settings

logger = logging.getLogger(__name__)


class TelemetryManager:
    """Manages OpenTelemetry instrumentation."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.tracer_provider: TracerProvider | None = None
        self.meter_provider: MeterProvider | None = None

    def setup(self) -> None:
        """Initialize OpenTelemetry instrumentation."""
        if not self.settings.otel_enabled:
            logger.info("OpenTelemetry is disabled")
            return

        logger.info("Initializing OpenTelemetry instrumentation")

        # Create resource with service information
        resource = self._create_resource()

        # Setup tracing
        self._setup_tracing(resource)

        # Setup metrics
        self._setup_metrics(resource)

        # Instrument libraries
        self._instrument_libraries()

        logger.info("OpenTelemetry instrumentation initialized successfully")

    def _create_resource(self) -> Resource:
        """Create resource with service attributes."""
        attributes = {
            ResourceAttributes.SERVICE_NAME: self.settings.otel_service_name,
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: self.settings.environment,
        }

        # Add custom resource attributes
        custom_attrs = self.settings.get_resource_attributes()
        attributes.update(custom_attrs)

        return Resource.create(attributes)

    def _setup_tracing(self, resource: Resource) -> None:
        """Setup trace provider and exporters."""
        self.tracer_provider = TracerProvider(resource=resource)

        # Add span processor based on configuration
        if self.settings.otel_traces_exporter == "otlp":
            # OTLP exporter
            otlp_exporter = OTLPSpanExporter(
                endpoint=f"{self.settings.otel_exporter_otlp_endpoint}/v1/traces"
                if not self.settings.otel_exporter_otlp_endpoint.endswith("/v1/traces")
                else self.settings.otel_exporter_otlp_endpoint,
                headers=self.settings.get_otlp_headers(),
            )
            self.tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info(
                f"OTLP trace exporter configured: {self.settings.otel_exporter_otlp_endpoint}"
            )

        elif self.settings.otel_traces_exporter == "console":
            # Console exporter for debugging
            console_exporter = ConsoleSpanExporter()
            self.tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
            logger.info("Console trace exporter configured")

        # Set as global tracer provider
        trace.set_tracer_provider(self.tracer_provider)

    def _setup_metrics(self, resource: Resource) -> None:
        """Setup meter provider and exporters."""
        if self.settings.otel_metrics_exporter == "otlp":
            # OTLP metric exporter
            otlp_exporter = OTLPMetricExporter(
                endpoint=f"{self.settings.otel_exporter_otlp_endpoint}/v1/metrics"
                if not self.settings.otel_exporter_otlp_endpoint.endswith("/v1/metrics")
                else self.settings.otel_exporter_otlp_endpoint,
                headers=self.settings.get_otlp_headers(),
            )
            reader = PeriodicExportingMetricReader(otlp_exporter, export_interval_millis=60000)
            self.meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
            logger.info(
                f"OTLP metric exporter configured: {self.settings.otel_exporter_otlp_endpoint}"
            )

        elif self.settings.otel_metrics_exporter == "console":
            # Console exporter for debugging
            from opentelemetry.sdk.metrics.export import ConsoleMetricExporter

            console_exporter = ConsoleMetricExporter()
            reader = PeriodicExportingMetricReader(console_exporter, export_interval_millis=60000)
            self.meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
            logger.info("Console metric exporter configured")

        else:
            # No metrics exporter
            self.meter_provider = MeterProvider(resource=resource)

        # Set as global meter provider
        metrics.set_meter_provider(self.meter_provider)

    def _instrument_libraries(self) -> None:
        """Auto-instrument common libraries."""
        # SQLAlchemy instrumentation will be done when engine is created
        # FastAPI instrumentation will be done when app is created
        # HTTPXClient instrumentation
        HTTPXClientInstrumentor().instrument()
        logger.info("HTTPX client instrumented")

    def shutdown(self) -> None:
        """Shutdown telemetry providers."""
        if self.tracer_provider:
            self.tracer_provider.shutdown()
        if self.meter_provider:
            self.meter_provider.shutdown()
        logger.info("OpenTelemetry shutdown complete")


# OpenInference span attribute helpers
class OpenInferenceSpanKind:
    """OpenInference span kind values."""

    AGENT = "AGENT"
    LLM = "LLM"
    CHAIN = "CHAIN"
    TOOL = "TOOL"
    RETRIEVER = "RETRIEVER"


def set_span_attributes(span: Any, **attributes: Any) -> None:
    """Set multiple attributes on a span."""
    for key, value in attributes.items():
        if value is not None:
            if isinstance(value, (dict, list)):
                import json

                span.set_attribute(key, json.dumps(value))
            else:
                span.set_attribute(key, str(value))


def create_llm_span_attributes(
    model: str,
    system_prompt: str,
    input_messages: list[dict],
    output_messages: list[dict] | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
    tools: list[dict] | None = None,
) -> dict[str, Any]:
    """Create OpenInference-compliant LLM span attributes."""
    import json

    attributes = {
        "openinference.span.kind": OpenInferenceSpanKind.LLM,
        "gen_ai.system": "openai",  # OpenRouter uses OpenAI-compatible API
        "gen_ai.request.model": model,
        "gen_ai.operation.name": "chat",
        "llm.model_name": model,
        "llm.system": system_prompt,
        "llm.input_messages": json.dumps(input_messages),
    }

    if output_messages:
        attributes["llm.output_messages"] = json.dumps(output_messages)

    if tools:
        attributes["llm.tools"] = json.dumps({"count": len(tools), "functions": tools})

    if session_id:
        attributes["session.id"] = session_id

    if user_id:
        attributes["user.id"] = str(user_id)

    return attributes


def create_agent_span_attributes(
    session_id: str,
    user_id: str | None,
    input_value: str,
    output_value: str | None = None,
) -> dict[str, Any]:
    """Create OpenInference-compliant agent span attributes."""
    attributes = {
        "openinference.span.kind": OpenInferenceSpanKind.AGENT,
        "session.id": session_id,
        "input.value": input_value,
    }

    if user_id:
        attributes["user.id"] = str(user_id)

    if output_value:
        attributes["output.value"] = output_value

    return attributes
