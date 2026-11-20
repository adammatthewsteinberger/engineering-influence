# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ApiRuntime."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


class ApiRuntimeInterface(ABC):
    """Build the API from settings and serve it."""

    __slots__ = ()

    @abstractmethod
    def build_app(self) -> Any:
        """Wire the ledger, the correlating queue, the guard and observability."""

    @abstractmethod
    def run(self) -> None:
        """Configure logging, build the app, and serve until stopped."""

    @abstractmethod
    def close(self) -> None:
        """Dispose of the database pool."""
