# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""OtelTracing: with no endpoint nothing changes; with one, the API records a span per request and the provider is installed.

Installing a provider is process-wide, so the endpoint cases run in a child process.
"""

import subprocess
import sys
import textwrap
from pathlib import Path

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from engineering_influence.infrastructure.observability.otel_tracing import OtelTracing

ROOT = Path(__file__).resolve().parents[3]


def child(code: str) -> str:
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_without_an_endpoint_the_app_is_left_alone() -> None:
    app = FastAPI()
    OtelTracing().attach(app, "", "engineering-influence-api")
    assert not getattr(app, "_is_instrumented_by_opentelemetry", False)


def test_without_an_endpoint_no_provider_is_installed() -> None:
    OtelTracing().start("  ", "engineering-influence-worker")
    assert not isinstance(trace.get_tracer_provider(), TracerProvider)


def test_with_an_endpoint_the_api_is_instrumented_and_the_provider_named_for_it() -> None:
    output = child(
        """
        from fastapi import FastAPI
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from engineering_influence.infrastructure.observability.otel_tracing import OtelTracing
        app = FastAPI()
        OtelTracing().attach(app, "http://127.0.0.1:9", "engineering-influence-api")
        provider = trace.get_tracer_provider()
        print(getattr(app, "_is_instrumented_by_opentelemetry", False))
        print(isinstance(provider, TracerProvider), provider.resource.attributes["service.name"])
        """
    )
    assert output.splitlines() == ["True", "True engineering-influence-api"]


def test_with_an_endpoint_the_worker_installs_its_provider() -> None:
    output = child(
        """
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from engineering_influence.infrastructure.observability.otel_tracing import OtelTracing
        OtelTracing().start("http://127.0.0.1:9", "engineering-influence-worker")
        provider = trace.get_tracer_provider()
        print(isinstance(provider, TracerProvider), provider.resource.attributes["service.name"])
        """
    )
    assert output.strip() == "True engineering-influence-worker"
