# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Run journal held in memory, for local demonstrations and tests."""

from engineering_influence.interfaces.journal_interface import JournalInterface
from engineering_influence.models.journal_entry import JournalEntry


class InMemoryJournal(JournalInterface):
    """Keeps entries in recording order; the first entry for a request wins."""

    def __init__(self) -> None:
        self._entries: list[JournalEntry] = []

    def record(self, entry: JournalEntry) -> JournalEntry:
        existing = self.find(entry.run_id, entry.stage, entry.key.digest())
        if existing is not None:
            return existing
        self._entries.append(entry)
        return entry

    def find(self, run_id: str, stage: str, digest: str) -> JournalEntry | None:
        for entry in self._entries:
            if (entry.run_id, entry.stage, entry.key.digest()) == (run_id, stage, digest):
                return entry
        return None

    def entries(self, run_id: str) -> list[JournalEntry]:
        return [entry for entry in self._entries if entry.run_id == run_id]
