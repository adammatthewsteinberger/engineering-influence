# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: reading the errors and warnings out of a publication report."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PublicationFindingsInterface(ABC):
    """Turns the findings of the manuscript audit and the release check into plain messages."""

    __slots__ = ()

    @staticmethod
    @abstractmethod
    def errors(result: dict[str, Any]) -> tuple[str, ...]:
        """What stops a release."""

    @staticmethod
    @abstractmethod
    def warnings(result: dict[str, Any]) -> tuple[str, ...]:
        """What the author should look at, and does not stop a release."""
