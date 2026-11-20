# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for StylesheetCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.epub.epub_contents import EpubContents


class StylesheetCheckInterface(ABC):
    """Kindle cannot resolve a link whose target is, or sits inside, a hidden element."""

    __slots__ = ()

    @abstractmethod
    def run(self, contents: EpubContents) -> list[str]:
        """Return a problem for each stylesheet that uses display:none."""
