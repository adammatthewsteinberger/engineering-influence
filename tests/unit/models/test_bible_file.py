# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""BibleFile: a card's kind is its folder and its id is its file name, and both must be lowercase identifiers."""

import pytest

from engineering_influence.models.bible_file import BibleFile


def test_a_card_file_names_its_kind_and_id() -> None:
    file = BibleFile("character", "ada-lovelace", "+++\n+++\n")
    assert file.path() == "character/ada-lovelace.md"


@pytest.mark.parametrize("kind", ["Character", "9places", "two words", ""])
def test_a_kind_must_be_a_lowercase_identifier(kind: str) -> None:
    with pytest.raises(ValueError, match="bible kind"):
        BibleFile(kind, "ada", "")


@pytest.mark.parametrize("card_id", ["Ada", "-ada", "ada lovelace", ""])
def test_an_id_must_be_a_lowercase_identifier(card_id: str) -> None:
    with pytest.raises(ValueError, match="bible id"):
        BibleFile("character", card_id, "")
