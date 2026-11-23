# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""AuthorProfile: the author's own details, required where the build needs them, readable text throughout."""

from typing import Any

import pytest

from engineering_influence.models.author_profile import AuthorProfile
from engineering_influence.models.interfaces.author_profile_interface import (
    AuthorProfileInterface,
)


def profile(**changes: Any) -> AuthorProfile:
    fields: dict[str, Any] = {
        "author": "Ann Author",
        "publisher": "Pub House",
        "edition": "First Edition",
        "author_bio": "Ann writes.\n\nAnd more.",
    }
    return AuthorProfile(**{**fields, **changes})


def refused(**changes: Any) -> str:
    with pytest.raises((ValueError, TypeError)) as error:
        profile(**changes)
    return str(error.value)


def test_a_profile_needs_an_author_a_publisher_an_edition_and_a_bio() -> None:
    made = profile()
    assert isinstance(made, AuthorProfileInterface)
    for field in ("author", "publisher", "edition", "author_bio"):
        assert refused(**{field: ""}) == f"{field} is required"


def test_only_what_is_set_is_written_to_the_config_in_a_fixed_order() -> None:
    assert list(profile().entries()) == ["author", "publisher", "edition", "author_bio"]
    full = profile(
        year=2031,
        website="https://pub.example",
        email="a@pub.example",
        isbn="978-1-2345-6789-0",
        ebook_isbn="9781234567890",
        dedication="For you.",
        copyright_notes="Some notes.",
        also_by=("Earlier Book", "Another"),
    )
    assert list(full.entries()) == [
        "author",
        "publisher",
        "edition",
        "year",
        "author_bio",
        "website",
        "email",
        "isbn",
        "ebook_isbn",
        "dedication",
        "copyright_notes",
        "also_by",
    ]
    assert full.entries()["also_by"] == ["Earlier Book", "Another"]
    assert full.entries()["year"] == 2031


def test_the_edition_has_to_say_edition() -> None:
    assert (
        refused(edition="First printing")
        == "the edition has to say 'Edition', as in 'First Edition'"
    )
    assert profile(edition="Second Edition, revised")


@pytest.mark.parametrize("field", ["author", "publisher", "edition", "website", "email"])
def test_one_line_fields_are_one_visible_line_within_the_limit(field: str) -> None:
    base = {"edition": "Edition"}
    assert "one line" in refused(**{**base, field: "two\nlines"})
    assert "one line" in refused(**{**base, field: " padded"})
    assert "control or invisible" in refused(**{**base, field: "a" + chr(0x200B) + "b"})
    assert "longer than 200" in refused(**{**base, field: "x" * 201})


def test_a_bio_a_dedication_and_notes_may_run_to_paragraphs_but_stay_readable() -> None:
    for field in ("author_bio", "dedication", "copyright_notes"):
        assert profile(**{field: "One.\n\n\tTwo."})
        assert "control or invisible" in refused(**{field: "a" + chr(0x7F)})
        assert "control or invisible" in refused(**{field: "a" + chr(0x202E)})
        assert "longer than 4000" in refused(**{field: "x" * 4_001})
    assert profile(dedication="x" * 4_000)
    assert refused(dedication="  ") == "dedication is blank"
    assert refused(copyright_notes="\n") == "copyright_notes is blank"


def test_the_year_is_a_four_digit_number() -> None:
    assert profile(year=1000) and profile(year=9999)
    for bad in (999, 10_000, True, "2031"):
        assert refused(year=bad) == "the year is a four digit number"


def test_an_email_has_an_at_sign_and_no_space() -> None:
    assert profile(email="a@b.example")
    assert refused(email="nobody") == "the email is not an address"
    assert refused(email="a b@c.example") == "the email is not an address"


def test_isbns_are_digits_and_hyphens_ending_in_a_digit_or_x() -> None:
    assert profile(isbn="0-306-40615-X", ebook_isbn="9781234567897")
    for field in ("isbn", "ebook_isbn"):
        for bad in ("12", "abcdefghijk", "978-1-2345-6789-", "978 1 2345 6789 0"):
            assert (
                refused(**{field: bad}) == f"{field} is digits and hyphens, ending in a digit or X"
            )


def test_also_by_is_a_tuple_of_at_most_twenty_titles_each_one_line() -> None:
    assert profile(also_by=tuple(f"T{n}" for n in range(20)))
    assert "at most 20" in refused(also_by=tuple(f"T{n}" for n in range(21)))
    assert "at most 20" in refused(also_by=["one"])
    assert refused(also_by=("",)) == "an also_by title is required"
    assert "one line" in refused(also_by=("a\nb",))


def test_text_fields_must_be_text() -> None:
    assert refused(author=3) == "author is text"
    assert refused(author_bio=3) == "author_bio is text"
