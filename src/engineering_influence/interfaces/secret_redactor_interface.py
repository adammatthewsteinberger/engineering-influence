# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: removes secrets from data on its way into a cassette."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SecretRedactorInterface(ABC):
    """Masks secrets in JSON-shaped data."""

    __slots__ = ()

    @abstractmethod
    def redact(self, value: Any) -> Any:
        """The same data with every secret replaced by a mask."""

    @abstractmethod
    def leaks(self, value: Any) -> bool:
        """True when the data still holds something that redacting would change."""
