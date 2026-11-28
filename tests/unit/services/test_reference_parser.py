# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ReferenceParser: references are found by book, chapter and verse, and anything that is not a book is left alone."""

import pytest

from engineering_influence.services.interfaces.reference_parser_interface import (
    ReferenceParserInterface,
)
from engineering_influence.services.reference_parser import ReferenceParser


def labels(text: str) -> list[list[str]]:
    return [[verse.label() for verse in verses] for _, _, verses in ReferenceParser().find(text)]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("(John 3:16)", [["JHN 3:16"]]),
        ("see Gen. 1:1", [["GEN 1:1"]]),
        ("Romans 8:28-30 says so", [["ROM 8:28", "ROM 8:29", "ROM 8:30"]]),
        ("1 Cor. 13:4–7", [["1CO 13:4", "1CO 13:5", "1CO 13:6", "1CO 13:7"]]),
        ("1 John 4:8", [["1JN 4:8"]]),
        ("Song of Solomon 2:1", [["SNG 2:1"]]),
        ("Ps 23:1 and Psalm 1:1", [["PSA 23:1"], ["PSA 1:1"]]),
    ],
)
def test_a_reference_names_its_book_chapter_and_verses(
    text: str, expected: list[list[str]]
) -> None:
    assert labels(text) == expected


def test_each_reference_is_reported_with_where_it_is_in_the_text() -> None:
    text = "as John 3:16 and Ps 23:1 say"
    found = ReferenceParser().find(text)
    assert [(start, end) for start, end, _ in found] == [(3, 12), (17, 24)]
    assert text[found[0][0] : found[0][1]] == "John 3:16"


@pytest.mark.parametrize(
    "text",
    [
        "the sermon 3:16",
        "Jesus 3:16",
        "Romans 5:9-3",
        "Romans 5:1-99",
        "Genesis 1:0",
        "no reference here",
    ],
)
def test_text_that_is_not_a_reference_is_left_alone(text: str) -> None:
    assert ReferenceParser().find(text) == ()


def test_it_is_a_reference_parser() -> None:
    assert isinstance(ReferenceParser(), ReferenceParserInterface)
