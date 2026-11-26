# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""SourceFile: a file name, never a path, and text without control characters."""

import pytest

from engineering_influence.models.source_file import SourceFile


def test_a_source_file_keeps_its_text() -> None:
    assert (
        SourceFile("01-opening.md", "Chapter one.\tA tab is plain.\n").text()
        == "Chapter one.\tA tab is plain.\n"
    )


@pytest.mark.parametrize(
    "name", ["", "../secret.md", "sub/chapter.md", "back\\slash.md", ".", ".."]
)
def test_a_path_is_not_a_file_name(name: str) -> None:
    with pytest.raises(ValueError, match="file name, not a path"):
        SourceFile(name, "text")


def test_control_characters_are_refused() -> None:
    with pytest.raises(ValueError, match="control characters"):
        SourceFile("chapter.md", "text\x00with a nul")
