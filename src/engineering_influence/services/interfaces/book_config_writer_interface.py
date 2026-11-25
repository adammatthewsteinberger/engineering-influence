# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for BookConfigWriter."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.author_profile import AuthorProfile
    from engineering_influence.models.book_metadata import BookMetadata


class BookConfigWriterInterface(ABC):
    """Writes the TOML config of an assembled book."""

    __slots__ = ()

    @abstractmethod
    def write(
        self,
        kind: str,
        metadata: BookMetadata,
        profile: AuthorProfile | None,
        trim_size: str | None,
        chapters: tuple[str, ...],
    ) -> str:
        """The config text: the listing, the author's details when there are any, and the chapter files."""
