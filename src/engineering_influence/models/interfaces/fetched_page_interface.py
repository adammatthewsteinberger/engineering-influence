# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for FetchedPage."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.source_record import SourceRecord


class FetchedPageInterface(ABC):
    """A page that was fetched and read."""

    __slots__ = ()

    @abstractmethod
    def content_hash(self) -> str:
        """The SHA-256 of the text, which is what the source is pinned by."""

    @abstractmethod
    def to_source(self) -> SourceRecord:
        """The source record for this page, not yet verified against any claim."""
