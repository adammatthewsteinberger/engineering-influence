# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""FilesystemSourceLibrary: Markdown and text files, in name order, refusing what is missing or too large."""

from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.source_library.filesystem_source_library import (
    FilesystemSourceLibrary,
)


def test_markdown_and_text_files_are_read_in_name_order(tmp_path: Path) -> None:
    (tmp_path / "b.txt").write_text("Second.", encoding="utf-8")
    (tmp_path / "a.md").write_text("First.", encoding="utf-8")
    (tmp_path / "notes.pdf").write_bytes(b"%PDF")
    (tmp_path / ".hidden.md").write_text("hidden", encoding="utf-8")
    files = FilesystemSourceLibrary().read(tmp_path)
    assert [(f.name, f.text()) for f in files] == [("a.md", "First."), ("b.txt", "Second.")]


def test_a_missing_folder_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ApplicationError) as error:
        FilesystemSourceLibrary().read(tmp_path / "missing")
    assert error.value.code == "SOURCE_FOLDER_MISSING"


def test_a_file_over_the_limit_is_refused_not_truncated(tmp_path: Path) -> None:
    (tmp_path / "long.md").write_bytes(b"x" * (FilesystemSourceLibrary.MAX_BYTES + 1))
    with pytest.raises(ApplicationError) as error:
        FilesystemSourceLibrary().read(tmp_path)
    assert error.value.code == "SOURCE_TOO_LARGE"
