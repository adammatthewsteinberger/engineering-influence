# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One finished model call, recorded so a resumed run does not pay for it again."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.journal_entry_interface import JournalEntryInterface
from engineering_influence.models.journal_key import JournalKey


@dataclass(frozen=True, slots=True)
class JournalEntry(JournalEntryInterface):
    """The answer a request got, what it cost, and where in the run it happened."""

    run_id: str
    stage: str
    attempt: int
    key: JournalKey
    response: str
    cost_micro_usd: int

    def __post_init__(self) -> None:
        """Validate the journal entry's answer and cost when it is built."""
        if not self.run_id.strip() or not self.stage.strip():
            raise ValueError("a journal entry needs a run and a stage")
        if self.attempt < 1:
            raise ValueError("attempts count from 1")
        if self.cost_micro_usd < 0:
            raise ValueError("a call cannot cost less than nothing")
