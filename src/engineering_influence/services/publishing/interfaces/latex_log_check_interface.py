# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for LatexLogCheck."""

from abc import ABC, abstractmethod


class LatexLogCheckInterface(ABC):
    """Flags typesetting defects the PDF itself cannot reveal."""

    __slots__ = ()

    @abstractmethod
    def run(self, log: str) -> list[str]:
        """Return a problem per missing glyph and one for overfull lines over 1pt."""
