# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for the reference EPUB validator."""

from abc import ABC, abstractmethod
from pathlib import Path


class EpubcheckInterface(ABC):
    """Validate an EPUB with epubcheck."""

    __slots__ = ()

    @abstractmethod
    def run(self, path: Path) -> list[str]:
        """Return the validator's findings; an empty list means it passed."""
