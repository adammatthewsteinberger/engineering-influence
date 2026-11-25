# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for checking the cover image inside a built EPUB."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.epub.epub_contents import EpubContents


class EpubCoverInspectorInterface(ABC):
    """Decode the cover image from the archive and judge it against the Kindle rules."""

    __slots__ = ()

    @abstractmethod
    def problems(self, contents: EpubContents, href: str) -> list[str]:
        """Return the problems with the image the OPF declares at href; empty when it is fine."""
