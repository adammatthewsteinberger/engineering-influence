# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PdfVerifier."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class PdfVerifierInterface(ABC):
    """Checks an interior PDF against KDP print rules and against itself."""

    __slots__ = ()

    @abstractmethod
    def verify(self, pdf_path: Path, config_path: Path, log_path: Path | None = None) -> list[str]:
        """Return every problem found; an empty list means the interior passes."""
