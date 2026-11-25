# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SourceRecord."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.source_record import SourceRecord


class SourceRecordInterface(ABC):
    """A source a non-fiction book leans on, pinned by the hash of what was fetched."""

    __slots__ = ()

    @abstractmethod
    def mark_verified(self) -> SourceRecord:
        """The same source once its text has been checked against the claim."""
