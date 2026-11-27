# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""OpenTelemetry spans for the API and the worker, exported over OTLP/HTTP to a collector such as Tempo."""

from typing import Any

from engineering_influence.infrastructure.observability.interfaces.otel_tracing_interface import (
    OtelTracingInterface,
)


class OtelTracing(OtelTracingInterface):
    """The provider and the exporter are built here; the runtime decides when to install the provider globally.

    Nothing is exported unless an endpoint is set (EI_OTLP_ENDPOINT). The endpoint is a base address; spans go to
    its /v1/traces path.
    """

    TRACES_PATH = "/v1/traces"

    def attach(self, app: Any, endpoint: str, service: str) -> None:
        provider = self._provider(endpoint, service)
        if provider is None:
            return
        self._instrument(app, provider)
        self._install(provider)

    def start(self, endpoint: str, service: str) -> None:
        provider = self._provider(endpoint, service)
        if provider is not None:
            self._install(provider)

    def _provider(self, endpoint: str, service: str) -> Any:
        """A provider exporting to the endpoint, or None when the endpoint is empty. Installs nothing."""
        if not endpoint.strip():
            return None
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(resource=Resource.create({"service.name": service}))
        exporter = OTLPSpanExporter(endpoint=endpoint.rstrip("/") + self.TRACES_PATH)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        return provider

    @staticmethod
    def _install(provider: Any) -> None:
        from opentelemetry import trace

        trace.set_tracer_provider(provider)

    @staticmethod
    def _instrument(app: Any, provider: Any) -> None:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
