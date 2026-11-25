# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for MarkdownLatexConverter."""

from abc import ABC, abstractmethod


class MarkdownLatexConverterInterface(ABC):
    """Converts a chapter body (without its title) to LaTeX."""

    __slots__ = ()

    @abstractmethod
    def convert(self, body: str, *, style: str, scene_breaks: bool = False) -> str:
        """Return the LaTeX for the body in the given chapter style."""
