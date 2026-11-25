# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: publishing and packaging one book of a project."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BookPublisherInterface(ABC):
    """Runs a book through every gate and writes its release bundle."""

    __slots__ = ()

    @abstractmethod
    def publish(
        self, slug: str, *, no_render: bool = False, strict_release: bool = False
    ) -> tuple[dict[str, Any], bool]:
        """The publication report, and whether every gate passed."""

    @abstractmethod
    def package(self, slug: str) -> str:
        """Write the release bundle of a book that passed; refused for one whose release check fails."""
