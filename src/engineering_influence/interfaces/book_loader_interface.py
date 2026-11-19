# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for loading a configured book and its manuscripts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.typesetting.book import Book


class BookLoaderInterface(ABC):
    """Read a book config and the Markdown it names into a Book."""

    __slots__ = ()

    @abstractmethod
    def load(self, config_path: Path) -> Book:
        """Return the book described by the config; raise ManuscriptError when it is invalid."""
