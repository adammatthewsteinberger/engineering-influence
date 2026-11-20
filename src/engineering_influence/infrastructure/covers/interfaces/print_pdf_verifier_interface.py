# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PrintPdfVerifier."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class PrintPdfVerifierInterface(ABC):
    """A single unencrypted page of exact size holding one flattened RGB image."""

    __slots__ = ()

    @abstractmethod
    def run(self, path: Path, width_in: float, height_in: float) -> list[str]:
        """Return problems with the PDF."""
