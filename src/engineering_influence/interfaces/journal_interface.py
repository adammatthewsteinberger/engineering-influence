# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Run journal port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.journal_entry import JournalEntry


class JournalInterface(ABC):
    """Remember each finished model call so a resumed run can replay it."""

    __slots__ = ()

    @abstractmethod
    def record(self, entry: JournalEntry) -> JournalEntry:
        """Store the entry; if its run, stage and request were recorded before, keep and return the first."""

    @abstractmethod
    def spend(self, entry: JournalEntry) -> None:
        """Count a paid call whose answer another worker recorded first, so the run's spend includes it. Replay still
        answers with the first entry for the request."""

    @abstractmethod
    def find(self, run_id: str, stage: str, digest: str) -> JournalEntry | None:
        """The recorded answer to a request, or None if it has not been made."""

    @abstractmethod
    def entries(self, run_id: str) -> list[JournalEntry]:
        """Everything recorded for a run, in the order it was recorded."""
