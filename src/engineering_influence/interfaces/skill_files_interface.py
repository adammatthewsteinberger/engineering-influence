# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: the skill files kept beside the lock."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class SkillFilesInterface(ABC):
    """Reads, writes and removes the text of skills, one file each."""

    __slots__ = ()

    @abstractmethod
    def read(self, path: Path) -> bytes | None:
        """The file's bytes, or None when there is no such file.

        Anything that is not a plain file of a reasonable size (a link, a folder, a huge file) is an
        ApplicationError, because a skill is text a person reviewed and not something to follow.
        """

    @abstractmethod
    def write(self, path: Path, data: bytes, replace: bool) -> None:
        """Write the file whole or not at all; an existing file is replaced only if asked."""

    @abstractmethod
    def remove(self, path: Path) -> None:
        """Delete the file; it is not an error that it is already gone."""
