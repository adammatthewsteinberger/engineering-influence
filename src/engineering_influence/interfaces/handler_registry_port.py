# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Vibey handler registry port."""

from abc import ABC, abstractmethod
from typing import Any


class HandlerRegistryPort(ABC):
    """Register custom job handlers for an external worker runtime."""

    @abstractmethod
    def register_handler(self, kind: str, handler: Any) -> None:
        """Register a long-lived handler."""

    @abstractmethod
    def register_factory(self, kind: str, factory: Any) -> None:
        """Register a per-job factory."""

    @abstractmethod
    def build_dispatcher(self) -> Any:
        """Return the external runtime dispatcher."""
