# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: the SHA-256 of a file."""

from __future__ import annotations

from abc import ABC, abstractmethod


class FileHasherInterface(ABC):
    """Hashes the contents of a regular file."""

    __slots__ = ()

    @abstractmethod
    def digest(self, path: str) -> str | None:
        """The SHA-256 of the file's contents in lowercase hex, or None if it is not a readable regular file."""
