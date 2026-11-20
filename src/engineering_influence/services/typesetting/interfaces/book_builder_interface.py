# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for BookBuilder."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class BookBuilderInterface(ABC):
    """Writes the .tex source, compiles it, and copies the PDF to the output directory."""

    __slots__ = ()

    @abstractmethod
    def build(self, slug: str, *, tex_only: bool = False, hardcover: bool = False) -> Path:
        """Return the .tex path when tex_only, otherwise the finished PDF path."""
