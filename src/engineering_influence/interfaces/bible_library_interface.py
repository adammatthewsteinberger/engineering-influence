# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: the bible cards and the schema an author has put in a folder."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from engineering_influence.models.bible_file import BibleFile


class BibleLibraryInterface(ABC):
    """Reads one bible folder. The domain never touches the file system."""

    __slots__ = ()

    @abstractmethod
    def read(self, folder: Path) -> tuple[BibleFile, ...]:
        """Every card file in the folder, one subfolder per kind. Raise an ApplicationError when the folder is missing."""

    @abstractmethod
    def schema(self, folder: Path) -> str:
        """The text of the folder's `bible.toml`, or an empty string when it has none."""
