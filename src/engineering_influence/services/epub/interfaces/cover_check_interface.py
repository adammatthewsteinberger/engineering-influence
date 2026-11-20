# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for CoverCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.epub.epub_contents import EpubContents


class CoverCheckInterface(ABC):
    """The Kindle Publishing Guidelines require an internal cover declared in the OPF."""

    __slots__ = ()

    @abstractmethod
    def run(self, contents: EpubContents) -> list[str]:
        """Return problems with the cover declaration and image."""
