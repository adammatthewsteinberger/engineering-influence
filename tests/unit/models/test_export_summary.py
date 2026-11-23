# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ExportSummary: how many files an export wrote and how many are the book."""

from typing import Any

import pytest

from engineering_influence.models.export_summary import ExportSummary
from engineering_influence.models.interfaces.export_summary_interface import (
    ExportSummaryInterface,
)


def test_a_summary_counts_the_files_and_the_ones_that_are_the_book() -> None:
    made = ExportSummary(5, 3)
    assert isinstance(made, ExportSummaryInterface)
    assert (made.files, made.book_files) == (5, 3)
    assert ExportSummary(1, 0) and ExportSummary(1, 1)


@pytest.mark.parametrize(("files", "book"), [(0, 0), (-1, 0), (2, 3), (2, -1)])
def test_an_export_wrote_something_and_the_book_is_some_of_it(files: int, book: int) -> None:
    with pytest.raises(ValueError, match="at least one file"):
        ExportSummary(files, book)


@pytest.mark.parametrize("bad", [1.5, "2", True, None])
def test_the_counts_are_whole_numbers(bad: Any) -> None:
    for files, book in ((bad, 0), (2, bad)):
        with pytest.raises(TypeError, match="whole files"):
            ExportSummary(files, book)
