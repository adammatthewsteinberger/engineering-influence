# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: putting a project's files on disk."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


class ProjectFilesWriterInterface(ABC):
    """Writes files, given as relative paths and bytes, into a folder that did not hold anything."""

    __slots__ = ()

    @abstractmethod
    def write(self, root: Path, files: Mapping[str, bytes]) -> None:
        """Write every file under ``root`` or none of them; an ApplicationError (EXPORT_TARGET_NOT_EMPTY) when ``root`` already holds something."""
