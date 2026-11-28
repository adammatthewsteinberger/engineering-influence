# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ScreenplayTitleParser and ScreenplayTitle: a film's title.toml gives its credit and source, and a file that breaks the
rules is refused by name."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.screenplay_title import ScreenplayTitle
from engineering_influence.services.screenplay_title_parser import ScreenplayTitleParser


def refused(text: str) -> str:
    with pytest.raises(ApplicationError) as error:
        ScreenplayTitleParser().parse(text)
    assert error.value.code == "SCREENPLAY_TITLE_INVALID"
    return error.value.message


def test_the_credit_and_source_are_read() -> None:
    title = ScreenplayTitleParser().parse('credit = "Based on the book by"\nsource = "Book One"\n')
    assert title == ScreenplayTitle("Based on the book by", "Book One")
    assert title.entries() == (("Credit", "Based on the book by"), ("Source", "Book One"))


def test_an_empty_file_gives_no_extra_entries() -> None:
    assert ScreenplayTitleParser().parse("").entries() == ()


def test_a_key_the_title_page_does_not_take_is_named() -> None:
    assert refused('colour = "red"\n') == (
        "title.toml it names keys the title page does not take: colour"
    )


def test_a_value_that_is_not_text_is_refused() -> None:
    assert refused("source = 3\n") == "title.toml source must be text"


def test_a_file_that_is_not_toml_is_refused() -> None:
    assert "is not valid TOML" in refused("credit = ")


def test_a_blank_value_is_refused() -> None:
    assert refused('credit = "   "\n') == "title.toml the title's credit cannot be blank"


def test_a_value_over_one_line_is_refused() -> None:
    assert refused('source = """two\nlines"""\n') == "title.toml the title's source is one line"


def test_a_value_over_the_length_limit_is_refused() -> None:
    long = "x" * (ScreenplayTitle.MAX_CHARS + 1)
    assert refused(f'source = "{long}"\n') == (
        f"title.toml the title's source is at most {ScreenplayTitle.MAX_CHARS} characters"
    )


def test_a_title_with_nothing_given_has_no_entries() -> None:
    assert ScreenplayTitle().entries() == ()
