# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ContentsPageCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.epub.epub_contents import EpubContents
    from engineering_influence.services.epub.toc_trees import TocTree


class ContentsPageCheckInterface(ABC):
    """The Kindle Publishing Guidelines want the toc nav in its own document, outside the."""

    __slots__ = ()

    @abstractmethod
    def run(self, contents: EpubContents, ncx_tree: TocTree | None) -> list[str]:
        """Return problems with the spine, guide, landmark, and contents page."""
