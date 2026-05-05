from __future__ import annotations

import json
import os
from typing import Any

_tracer = None


def init_tracer(service_name: str = "elvis-cli"):
    """Initialize OTEL tracer. No-op if neither HYPERDX_API_KEY nor OTEL_EXPORTER_OTLP_ENDPOINT is set."""
    global _tracer  # noqa: PLW0603

    hyperdx_key = os.environ.get("HYPERDX_API_KEY")
    otel_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")

    if not hyperdx_key and not otel_endpoint:
        return None

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.semconv.attributes import service_attributes

    resource = Resource.create(
        {
            service_attributes.SERVICE_NAME: service_name,
            service_attributes.SERVICE_VERSION: "0.1.0",
        },
    )

    endpoint = otel_endpoint
    if hyperdx_key and not endpoint:
        endpoint = os.environ.get(
            "HYPERDX_OTLP_ENDPOINT",
            "https://in-otel.hyperdx.io/v1/traces",
        )
    if not endpoint:
        return None

    headers: dict[str, str] = {}
    if hyperdx_key:
        headers["authorization"] = (
            hyperdx_key
            if hyperdx_key.lower().startswith("bearer ")
            else f"Bearer {hyperdx_key}"
        )

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, headers=headers)),
    )
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(service_name)
    return _tracer


def emit_cli_event(name: str, attributes: dict[str, Any]) -> None:
    """Fire-and-forget OTEL span event. No-op if tracer not initialized."""
    if _tracer is None:
        return
    with _tracer.start_as_current_span(name) as span:
        for key, value in attributes.items():
            if isinstance(value, (list, dict)):
                span.set_attribute(key, json.dumps(value))
            else:
                span.set_attribute(key, value)
