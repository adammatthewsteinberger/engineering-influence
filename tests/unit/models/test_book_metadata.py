# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""BookMetadata: the release contract's rules for a listing, held where the listing is made."""

from typing import Any

import pytest

from engineering_influence.models.book_metadata import BookMetadata
from engineering_influence.models.interfaces.book_metadata_interface import BookMetadataInterface

DESCRIPTION = " ".join(["Bees are easier to keep than most people think."] * 10)


def metadata(**changes: Any) -> BookMetadata:
    fields: dict[str, Any] = {
        "title": "Hive Mind",
        "subtitle": "A calm guide",
        "description": DESCRIPTION,
        "keywords": tuple(f"keyword {n}" for n in range(7)),
        "categories": ("Books > Science & Math",),
    }
    return BookMetadata(**{**fields, **changes})


def refused(**changes: Any) -> str:
    with pytest.raises((ValueError, TypeError)) as error:
        metadata(**changes)
    return str(error.value)


def test_a_listing_has_a_title_a_subtitle_a_description_keywords_and_categories() -> None:
    made = metadata()
    assert isinstance(made, BookMetadataInterface)
    assert (made.title, made.subtitle) == ("Hive Mind", "A calm guide")
    assert len(made.keywords) == 7 and made.categories == ("Books > Science & Math",)


@pytest.mark.parametrize("field", ["title", "subtitle"])
def test_a_title_and_a_subtitle_are_one_visible_line(field: str) -> None:
    assert refused(**{field: ""}) == f"the {field} is empty"
    assert "one line" in refused(**{field: " padded "})
    assert "one line" in refused(**{field: "two\nlines"})
    assert "control or invisible" in refused(**{field: "a" + chr(0x200B) + "b"})
    assert "control or invisible" in refused(**{field: "a" + chr(0x7F) + "b"})


def test_the_limits_on_each_text_are_exact() -> None:
    metadata(title="t" * 120, subtitle="s" * 200)
    assert "longer than 120" in refused(title="t" * 121)
    assert "longer than 200" in refused(subtitle="s" * 201)
    metadata(keywords=("k" * 50, *(f"k{n}" for n in range(6))))
    assert "longer than 50" in refused(keywords=("k" * 51, *(f"k{n}" for n in range(6))))
    metadata(categories=("Books > " + "c" * 192,))
    assert "longer than 200" in refused(categories=("Books > " + "c" * 193,))


def test_the_description_is_eighty_words_to_four_thousand_characters() -> None:
    eighty = " ".join(["word"] * 80)
    assert metadata(description=eighty).description == eighty
    assert refused(description=" ".join(["word"] * 79)) == (
        "the description has 79 words; a listing needs at least 80"
    )
    assert refused(description=" ") == "the description is empty"
    long = " ".join(["word"] * 800)
    assert len(long) == 3_999 and metadata(description=long)
    assert metadata(description=long + "s")
    assert "has 4001 characters" in refused(description=long + "ss")
    assert "control or invisible" in refused(description=DESCRIPTION + chr(0x202E))


def test_a_description_may_have_paragraphs() -> None:
    assert metadata(description=DESCRIPTION + "\n\n" + DESCRIPTION)


def test_there_are_exactly_seven_keywords_and_they_differ_ignoring_case() -> None:
    assert refused(keywords=("a",) * 6).startswith("a listing has exactly 7 keywords, not 6")
    assert refused(keywords=tuple(str(n) for n in range(8))).startswith("a listing has exactly 7")
    assert (
        refused(keywords=("A", "a", *(f"k{n}" for n in range(5)))) == "the keywords must all differ"
    )
    assert refused(keywords=["a"] * 7) == "the keywords are a tuple"
    assert refused(keywords=("", *(f"k{n}" for n in range(6)))) == "a keyword is empty"


def test_there_are_one_to_three_categories_that_differ_and_are_paths() -> None:
    three = ("Books > A", "Books > B", "Books > C")
    assert metadata(categories=three).categories == three
    assert refused(categories=()) == "a listing has one to 3 categories, not 0"
    assert refused(categories=(*three, "Books > D")) == "a listing has one to 3 categories, not 4"
    assert refused(categories=("Books > A", "books > a")) == "the categories must all differ"
    assert refused(categories=["Books > A"]) == "the categories are a tuple"
    for bad in ("Books", "Books >", "> Books", "Books >  > A", "FIC009000"):
        assert "not a browse path" in refused(categories=(bad,))
