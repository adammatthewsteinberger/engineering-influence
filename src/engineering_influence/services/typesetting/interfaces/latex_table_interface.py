# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for LatexTable."""

from abc import ABC, abstractmethod


class LatexTableInterface(ABC):
    """Renders rows of already-rendered cells; the first row is the header."""

    __slots__ = ()

    @abstractmethod
    def render(self, rows: list[list[str]]) -> str:
        """Return the LaTeX table, or an empty string for no rows."""
