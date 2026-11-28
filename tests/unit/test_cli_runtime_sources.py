# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The command-line runtime reads a run's source folder with the folder library, numbered in name order."""

from pathlib import Path

from engineering_influence.runtime.cli_runtime import CliRuntime


def test_the_runtime_reads_a_source_folder_numbered_in_name_order(tmp_path: Path) -> None:
    (tmp_path / "b.md").write_text("two", encoding="utf-8")
    (tmp_path / "a.md").write_text("one", encoding="utf-8")
    entries = CliRuntime._read_sources(tmp_path)
    assert [(entry.number, entry.text) for entry in entries] == [(1, "one"), (2, "two")]


def test_the_runtime_reads_a_bible_folder_as_checked_cards(tmp_path: Path) -> None:
    (tmp_path / "character").mkdir()
    (tmp_path / "character" / "ada.md").write_text(
        '+++\nname = "Ada"\n+++\nKeeps the log.', encoding="utf-8"
    )
    cards = CliRuntime._read_bible(tmp_path)
    assert [(card.kind, card.id, card.fields["name"]) for card in cards] == [
        ("character", "ada", "Ada")
    ]


def test_the_runtime_reads_a_title_file_as_text_when_the_folder_has_one(tmp_path: Path) -> None:
    (tmp_path / "title.toml").write_text('source = "Book One"\n', encoding="utf-8")
    assert CliRuntime._read_title(tmp_path) == 'source = "Book One"\n'


def test_a_folder_without_a_title_file_gives_no_title(tmp_path: Path) -> None:
    assert CliRuntime._read_title(tmp_path) is None


def test_a_title_file_that_breaks_the_rules_is_refused_when_read(tmp_path: Path) -> None:
    import pytest

    from engineering_influence.errors.application_error import ApplicationError

    (tmp_path / "title.toml").write_text('colour = "red"\n', encoding="utf-8")
    with pytest.raises(ApplicationError) as error:
        CliRuntime._read_title(tmp_path)
    assert error.value.code == "SCREENPLAY_TITLE_INVALID"
