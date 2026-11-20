# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for building a book's cover files."""

from abc import ABC, abstractmethod
from pathlib import Path


class CoverBuilderInterface(ABC):
    """Render and verify every cover file for one book."""

    __slots__ = ()

    @abstractmethod
    def build(self, slug: str, preview: bool = False, hardcover_pdf: Path | None = None) -> Path:
        """Return the directory the covers were written to."""
