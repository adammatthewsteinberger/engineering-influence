# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""FilesystemBibleLibrary: one folder per kind, one Markdown card per file, bible.toml at the root."""

from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.bible_library.filesystem_bible_library import (
    FilesystemBibleLibrary,
)


def test_cards_are_read_by_kind_then_name_and_hidden_or_other_files_are_skipped(
    tmp_path: Path,
) -> None:
    (tmp_path / "place").mkdir()
    (tmp_path / "character").mkdir()
    (tmp_path / "character" / "bea.md").write_text("+++\n+++\nBea.", encoding="utf-8")
    (tmp_path / "character" / "ada.md").write_text("+++\n+++\nAda.", encoding="utf-8")
    (tmp_path / "character" / "notes.txt").write_text("not a card", encoding="utf-8")
    (tmp_path / "character" / ".draft.md").write_text("hidden", encoding="utf-8")
    (tmp_path / "place" / "harbour.md").write_text("+++\n+++\nThe harbour.", encoding="utf-8")
    (tmp_path / ".archive").mkdir()
    (tmp_path / ".archive" / "old.md").write_text("hidden", encoding="utf-8")
    (tmp_path / "readme.md").write_text("ignored at the root", encoding="utf-8")

    files = FilesystemBibleLibrary().read(tmp_path)

    assert [file.path() for file in files] == [
        "character/ada.md",
        "character/bea.md",
        "place/harbour.md",
    ]
    assert files[0].text == "+++\n+++\nAda."


def test_a_kind_folder_with_no_cards_contributes_none(tmp_path: Path) -> None:
    (tmp_path / "place").mkdir()
    (tmp_path / "place" / "map.png").write_bytes(b"png")
    assert FilesystemBibleLibrary().read(tmp_path) == ()


def test_the_schema_is_read_from_bible_toml_or_is_empty(tmp_path: Path) -> None:
    library = FilesystemBibleLibrary()
    assert library.schema(tmp_path) == ""
    (tmp_path / "bible.toml").write_text('[required]\ncharacter = ["name"]\n', encoding="utf-8")
    assert library.schema(tmp_path) == '[required]\ncharacter = ["name"]\n'


def test_a_missing_folder_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ApplicationError) as error:
        FilesystemBibleLibrary().read(tmp_path / "absent")
    assert error.value.code == "BIBLE_FOLDER_MISSING"


def test_a_missing_folder_has_no_schema_either(tmp_path: Path) -> None:
    with pytest.raises(ApplicationError) as error:
        FilesystemBibleLibrary().schema(tmp_path / "absent")
    assert error.value.code == "BIBLE_FOLDER_MISSING"


def test_a_kind_folder_name_the_bible_cannot_use_is_refused(tmp_path: Path) -> None:
    (tmp_path / "Places").mkdir()
    (tmp_path / "Places" / "harbour.md").write_text("+++\n+++\n", encoding="utf-8")
    with pytest.raises(ApplicationError) as error:
        FilesystemBibleLibrary().read(tmp_path)
    assert error.value.code == "BIBLE_CARD_INVALID"
    assert "Places/harbour.md" in error.value.message


def test_a_card_name_the_bible_cannot_use_is_refused(tmp_path: Path) -> None:
    (tmp_path / "character").mkdir()
    (tmp_path / "character" / "Ada Lovelace.md").write_text("+++\n+++\n", encoding="utf-8")
    with pytest.raises(ApplicationError) as error:
        FilesystemBibleLibrary().read(tmp_path)
    assert error.value.code == "BIBLE_CARD_INVALID"
