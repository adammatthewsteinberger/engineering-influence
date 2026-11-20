# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ImageVerifier."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class ImageVerifierInterface(ABC):
    """Checks a print panel against the exact KDP page size."""

    __slots__ = ()

    @abstractmethod
    def run(self, path: Path, width_in: float, height_in: float, ppi: float) -> list[str]:
        """Return problems with the file."""
