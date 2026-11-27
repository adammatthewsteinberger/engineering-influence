# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ScreenplayTitle."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ScreenplayTitleInterface(ABC):
    """What a film's title page says beyond its title."""

    __slots__ = ()

    @abstractmethod
    def entries(self) -> tuple[tuple[str, str], ...]:
        """The title page's extra entries, in the order they print."""
