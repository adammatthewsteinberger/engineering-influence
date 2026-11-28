# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A book a run produced."""

from dataclasses import dataclass

from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.interfaces.made_book_interface import MadeBookInterface


@dataclass(frozen=True, slots=True)
class MadeBook(MadeBookInterface):
    """What came of making one case: how the run ended, the chapters it wrote, and what it cost against what was expected.

    ``chapters`` are the chapter texts in order (empty when the run did not get as far as assembling a book).
    ``finished`` means the run completed and the book built; only a finished book is judged.
    """

    case: str
    kind: BookKind
    run_status: str
    finished: bool
    title: str
    chapters: tuple[str, ...]
    spent_micro_usd: int
    estimated_micro_usd: int | None
    issues: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate the made book's outcome and costs when it is built."""
        if not self.case.strip() or not self.run_status.strip():
            raise ValueError("a made book names its case and how its run ended")
        for label, value in (
            ("spent", self.spent_micro_usd),
            ("estimated", self.estimated_micro_usd),
        ):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{label} is a whole number of micro-dollars")
        if self.finished and not self.chapters:
            raise ValueError("a finished book has chapters")

    def text(self) -> str:
        """The book as the judge reads it: the title, then every chapter."""
        return "\n\n".join([f"# {self.title}", *self.chapters])
