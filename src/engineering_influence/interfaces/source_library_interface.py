# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: the source files an author has put in a folder."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from engineering_influence.models.source_file import SourceFile


class SourceLibraryInterface(ABC):
    """Reads the source files of one folder, in file-name order. The domain never touches the file system."""

    __slots__ = ()

    @abstractmethod
    def read(self, folder: Path) -> tuple[SourceFile, ...]:
        """Every readable source file in the folder, sorted by name. Raise an ApplicationError when the folder is missing."""
