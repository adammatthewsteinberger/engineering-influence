# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ScreenplayLatexSource."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ScreenplayLatexSourceInterface(ABC):
    """Turns a Fountain script into the LaTeX source of its printed pages."""

    __slots__ = ()

    @abstractmethod
    def render(self, script: str) -> str:
        """The LaTeX document for the script: a title page, then the elements in standard screenplay layout."""
