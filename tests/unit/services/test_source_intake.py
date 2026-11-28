# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""SourceIntake: a folder's sources, numbered and pinned, and an empty folder refused."""

import hashlib
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.source_library_interface import SourceLibraryInterface
from engineering_influence.models.source_file import SourceFile
from engineering_influence.services.source_intake import SourceIntake


class FakeLibrary(SourceLibraryInterface):
    """Returns the files it was given, whatever folder is asked for."""

    def __init__(self, files: tuple[SourceFile, ...]) -> None:
        self._files = files
        self.asked: list[Path] = []

    def read(self, folder: Path) -> tuple[SourceFile, ...]:
        self.asked.append(folder)
        return self._files


def test_sources_are_numbered_in_order_with_their_sha256() -> None:
    library = FakeLibrary((SourceFile("a.md", "First."), SourceFile("b.md", "Second.")))
    entries = SourceIntake(library).intake(Path("sources"))
    assert [e.number for e in entries] == [1, 2]
    assert [e.artifact() for e in entries] == ["source/001.md", "source/002.md"]
    assert entries[1].digest == hashlib.sha256(b"Second.").hexdigest()
    assert library.asked == [Path("sources")]


def test_an_empty_folder_is_refused() -> None:
    with pytest.raises(ApplicationError) as error:
        SourceIntake(FakeLibrary(())).intake(Path("empty"))
    assert error.value.code == "SOURCE_EMPTY"
