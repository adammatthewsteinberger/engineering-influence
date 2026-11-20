# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for InternalLinksCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.epub.epub_contents import EpubContents


class InternalLinksCheckInterface(ABC):
    """Walks the XHTML pages checking hrefs, titles, and empty blocks."""

    __slots__ = ()

    @abstractmethod
    def run(self, contents: EpubContents) -> list[str]:
        """Return problems found in the XHTML pages."""
