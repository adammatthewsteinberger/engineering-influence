# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for EpubBuilder."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class EpubBuilderInterface(ABC):
    """The ebook shares one Markdown to LaTeX conversion with the print interior."""

    __slots__ = ()

    @abstractmethod
    def build(self, slug: str, *, tex_only: bool = False) -> Path:
        """Return the ebook .tex path when tex_only, otherwise the finished EPUB path."""
