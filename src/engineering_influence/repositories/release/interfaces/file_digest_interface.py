# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for FileDigest."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class FileDigestInterface(ABC):
    """Hashes in 1 MiB blocks so large PDFs never load whole."""

    __slots__ = ()

    @abstractmethod
    def sha256(self, path: Path) -> str:
        """The hex digest of the file's bytes."""
