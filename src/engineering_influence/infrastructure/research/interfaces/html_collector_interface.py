# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for HtmlCollector."""

from __future__ import annotations

from abc import ABC, abstractmethod


class HtmlCollectorInterface(ABC):
    """Reads one HTML page and keeps the text a reader would see."""

    __slots__ = ()

    @abstractmethod
    def collected(self) -> tuple[str, str]:
        """The title and the visible text found so far, both before whitespace is cleaned up."""
