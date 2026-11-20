# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for LatexEscaper."""

from abc import ABC, abstractmethod


class LatexEscaperInterface(ABC):
    """Escapes LaTeX specials and applies light typographic fixes."""

    __slots__ = ()

    @abstractmethod
    def escape(self, text: str) -> str:
        """Return text safe to place in a LaTeX body."""
