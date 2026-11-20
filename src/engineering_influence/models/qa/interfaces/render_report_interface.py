# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for RenderReport."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


class RenderReportInterface(ABC):
    """Every page's size and blankness, plus the contact sheets that show them."""

    __slots__ = ()

    @property
    @abstractmethod
    def blank_pages(self) -> list[int]:
        """Numbers of pages that are visually blank."""

    @property
    @abstractmethod
    def unexpected_blank_pages(self) -> list[int]:
        """Pages in a blank run longer than the print pipeline permits (two)."""

    @abstractmethod
    def as_dict(self) -> dict[str, Any]:
        """A JSON-ready dictionary including the derived blank-page lists."""
