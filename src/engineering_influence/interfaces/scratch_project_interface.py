# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: laying a book's files out as a project in a scratch folder."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


class ScratchProjectInterface(ABC):
    """Writes the files of a project below a folder, refusing any path that would leave it."""

    __slots__ = ()

    @staticmethod
    @abstractmethod
    def write(root: Path, files: Mapping[str, bytes]) -> None:
        """Write each file below ``root``, which is already resolved."""
