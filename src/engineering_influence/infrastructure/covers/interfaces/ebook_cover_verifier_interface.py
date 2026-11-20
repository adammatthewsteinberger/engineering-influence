# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for EbookCoverVerifier."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class EbookCoverVerifierInterface(ABC):
    """Size, format, colour, compression, and the gray border on a light cover."""

    __slots__ = ()

    @abstractmethod
    def run(self, path: Path) -> list[str]:
        """Return problems with the file."""
