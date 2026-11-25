# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for XmlCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.epub.epub_contents import EpubContents


class XmlCheckInterface(ABC):
    """Parses each document and collects the reader-visible text of the XHTML pages."""

    __slots__ = ()

    @abstractmethod
    def run(self, contents: EpubContents) -> tuple[list[str], str]:
        """Return (problems, the XHTML text joined by newlines)."""
