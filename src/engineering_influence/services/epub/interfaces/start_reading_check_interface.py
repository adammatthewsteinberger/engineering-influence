# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for StartReadingCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.epub.epub_contents import EpubContents


class StartReadingCheckInterface(ABC):
    """EPUB 3 landmarks and the EPUB 2 guide both name where reading begins."""

    __slots__ = ()

    @abstractmethod
    def run(self, contents: EpubContents) -> list[str]:
        """Return problems with the start-of-text references."""
