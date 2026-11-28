# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Run journal held in memory, for local demonstrations and tests."""

from engineering_influence.interfaces.journal_interface import JournalInterface
from engineering_influence.models.journal_entry import JournalEntry


class InMemoryJournal(JournalInterface):
    """Keeps entries in recording order; the first entry for a request wins."""

    def __init__(self) -> None:
        """Start with no entries."""
        self._entries: list[JournalEntry] = []

    def record(self, entry: JournalEntry) -> JournalEntry:
        """Record the entry, or return the entry already recorded for the same stage and call."""
        existing = self.find(entry.run_id, entry.stage, entry.key.digest())
        if existing is not None:
            return existing
        self._entries.append(entry)
        return entry

    def spend(self, entry: JournalEntry) -> None:
        """Count a paid call whose answer another worker recorded first. find still returns the first entry, since it
        comes first in recording order."""
        self._entries.append(entry)

    def find(self, run_id: str, stage: str, digest: str) -> JournalEntry | None:
        """The first entry recorded for this run, stage and call digest, or None."""
        for entry in self._entries:
            if (entry.run_id, entry.stage, entry.key.digest()) == (run_id, stage, digest):
                return entry
        return None

    def entries(self, run_id: str) -> list[JournalEntry]:
        """Every entry recorded for the run, in the order they were recorded."""
        return [entry for entry in self._entries if entry.run_id == run_id]
