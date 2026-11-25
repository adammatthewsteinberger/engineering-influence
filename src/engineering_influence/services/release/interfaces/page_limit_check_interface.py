# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PageLimitCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class PageLimitCheckInterface(ABC):
    """Compares a built interior's page count with the limit."""

    __slots__ = ()

    @abstractmethod
    def run(self, path: Path, *, label: str, maximum: int) -> str | None:
        """A problem when the PDF exists and is too long; None otherwise."""
