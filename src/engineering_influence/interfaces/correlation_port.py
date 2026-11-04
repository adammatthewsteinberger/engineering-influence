# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Correlation port."""

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager


class CorrelationPort(ABC):
    """Carry one correlation id across a request, a queued job and an outbound call."""

    @abstractmethod
    def current(self) -> str | None:
        """Return the active correlation id, if any."""

    @abstractmethod
    def scope(self, correlation_id: str | None) -> AbstractContextManager[str]:
        """Activate an id (or a new one when None) for the duration of the block."""
