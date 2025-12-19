from __future__ import annotations

from typing import Optional
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

def setup_tracing(service_name: str, namespace: str, otlp_endpoint: str | None) -> None:
    resource = Resource.create({
        "service.name": service_name,
        "service.namespace": namespace,
    })
    provider = TracerProvider(resource=resource)
    if otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint.rstrip("/") + "/v1/traces")
        provider.add_span_processor(BatchSpanProcessor(exporter))
    else:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
