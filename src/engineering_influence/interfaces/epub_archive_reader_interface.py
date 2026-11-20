# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for reading a built EPUB."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.epub.epub_contents import EpubContents


class EpubArchiveReaderInterface(ABC):
    """Open an EPUB archive and decode the parts the checks inspect."""

    __slots__ = ()

    @abstractmethod
    def read(self, path: Path) -> EpubContents:
        """Return the decoded contents of the archive at path."""
