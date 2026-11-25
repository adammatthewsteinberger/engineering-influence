# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""VerseRef: a verse is a USFM book code, a chapter and a verse, all of them checked."""

import pytest

from engineering_influence.models.interfaces.verse_ref_interface import VerseRefInterface
from engineering_influence.models.verse_ref import VerseRef


def test_a_verse_is_labelled_as_a_reader_writes_it() -> None:
    assert VerseRef("JHN", 3, 16).label() == "JHN 3:16"
    assert VerseRef("1SA", 17, 45).label() == "1SA 17:45"


@pytest.mark.parametrize("book", ["jhn", "JOHN", "1S", "TOOLONG", ""])
def test_a_book_is_a_three_character_code(book: str) -> None:
    with pytest.raises(ValueError, match="book"):
        VerseRef(book, 1, 1)


@pytest.mark.parametrize(("chapter", "verse"), [(0, 1), (1, 0), (-2, 1), (1, -1)])
def test_a_chapter_and_a_verse_are_positive(chapter: int, verse: int) -> None:
    with pytest.raises(ValueError):
        VerseRef("GEN", chapter, verse)


def test_only_whole_numbers_are_chapters_and_verses() -> None:
    with pytest.raises(ValueError):
        VerseRef("GEN", True, 1)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        VerseRef("GEN", 1, 1.0)  # type: ignore[arg-type]


def test_it_is_a_verse_ref_interface() -> None:
    assert isinstance(VerseRef("GEN", 1, 1), VerseRefInterface)
