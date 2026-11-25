# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for MetadataParser."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_metadata import BookMetadata


class MetadataParserInterface(ABC):
    """Reads the metadata stage's markdown into a book's listing, strictly."""

    __slots__ = ()

    @abstractmethod
    def parse(self, text: str) -> BookMetadata:
        """The listing, or an ApplicationError (METADATA_INVALID) saying what is wrong with the text."""
