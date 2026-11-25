# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for checking an EPUB's ZIP container."""

from abc import ABC, abstractmethod
from pathlib import Path


class EpubZipCheckInterface(ABC):
    """Check the archive itself, without parsing any content."""

    __slots__ = ()

    @abstractmethod
    def run(self, path: Path) -> list[str]:
        """Return problems with the archive."""
