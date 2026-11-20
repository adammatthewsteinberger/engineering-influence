# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PathRelativizer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class PathRelativizerInterface(ABC):
    """Reports stable root-relative paths, falling back to the absolute path."""

    __slots__ = ()

    @abstractmethod
    def relative(self, path: Path) -> str:
        """Return the path relative to the root, or absolute when it lies outside."""
