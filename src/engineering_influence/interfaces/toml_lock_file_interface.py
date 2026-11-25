# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for reading and writing the TOML lock files."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class TomlLockFileInterface(ABC):
    """Reads, writes and quotes the TOML lock files."""

    __slots__ = ()

    @staticmethod
    @abstractmethod
    def read(path: Path, *, table: str, version: int, code: str) -> dict[str, Any] | None:
        """The parsed lock, or None when there is no file; refused with ``code`` when unusable."""

    @staticmethod
    @abstractmethod
    def write(path: Path, blocks: list[str]) -> None:
        """Write the lock whole, or not at all."""

    @staticmethod
    @abstractmethod
    def quote(text: str) -> str:
        """A TOML basic string."""
