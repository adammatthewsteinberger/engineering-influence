# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What an export of a run wrote."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.export_summary_interface import (
    ExportSummaryInterface,
)


@dataclass(frozen=True, slots=True)
class ExportSummary(ExportSummaryInterface):
    """``files`` in all, of which ``book_files`` are the manuscript project (the config and the chapters)."""

    files: int
    book_files: int

    def __post_init__(self) -> None:
        """Validate the file counts when the summary is built."""
        if type(self.files) is not int or type(self.book_files) is not int:
            raise TypeError("an export counts whole files")
        if not 0 <= self.book_files <= self.files or self.files < 1:
            raise ValueError("an export wrote at least one file, and the book is some of them")
