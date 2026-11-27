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
