# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for OtelTracing: exports spans to a collector when an endpoint is configured, and does nothing otherwise."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class OtelTracingInterface(ABC):
    """Spans over OTLP/HTTP. With an empty endpoint nothing is exported and the process is left as it was."""

    __slots__ = ()

    @abstractmethod
    def attach(self, app: Any, endpoint: str, service: str) -> None:
        """Instrument the API app so every HTTP request is a span, and install the provider."""

    @abstractmethod
    def start(self, endpoint: str, service: str) -> None:
        """Install the provider for a process with no HTTP app, such as the worker."""
