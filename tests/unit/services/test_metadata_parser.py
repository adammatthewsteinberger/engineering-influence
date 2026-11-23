# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""MetadataParser: the metadata stage's text is read into a listing, strictly, or refused with a reason."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.book_metadata import BookMetadata
from engineering_influence.services.dash_rewriter import DashRewriter
from engineering_influence.services.interfaces.metadata_parser_interface import (
    MetadataParserInterface,
)
from engineering_influence.services.metadata_parser import MetadataParser

EM = chr(0x2014)
SENTENCE = "Bees are easier to keep than most people think."
DESCRIPTION = " ".join([SENTENCE] * 10)
GOOD = """Title: Hive Mind
Subtitle: A calm guide to keeping bees
Description:
{description}
Keywords:
- beekeeping for beginners
- backyard bees
- how to start a hive
- honey bee care
- urban beekeeping
- bee colony basics
- hobby beekeeping
Categories:
- Books > Crafts, Hobbies & Home > Gardening & Landscape Design
- Books > Science & Math > Biological Sciences
"""
PARSER = MetadataParser(DashRewriter())


def listing(**changes: str) -> str:
    return GOOD.format(description=DESCRIPTION).replace(
        "Hive Mind", changes.get("title", "Hive Mind")
    )


def invalid(text: str) -> str:
    with pytest.raises(ApplicationError) as error:
        PARSER.parse(text)
    assert (error.value.code, error.value.http_status) == ("METADATA_INVALID", 422)
    assert error.value.message.startswith("the metadata cannot be read: ")
    return error.value.message.removeprefix("the metadata cannot be read: ")


def test_it_is_a_metadata_parser() -> None:
    assert isinstance(PARSER, MetadataParserInterface)


def test_the_format_the_stage_is_told_to_write_is_read_into_a_listing() -> None:
    made = PARSER.parse(listing())
    assert isinstance(made, BookMetadata)
    assert (made.title, made.subtitle) == ("Hive Mind", "A calm guide to keeping bees")
    assert made.description == DESCRIPTION
    assert made.keywords[0] == "beekeeping for beginners" and len(made.keywords) == 7
    assert made.categories == (
        "Books > Crafts, Hobbies & Home > Gardening & Landscape Design",
        "Books > Science & Math > Biological Sciences",
    )


def test_text_before_the_first_label_is_ignored() -> None:
    assert PARSER.parse("Here is the listing you asked for.\n\n" + listing()).title == "Hive Mind"


def test_labels_may_be_bold_in_either_style_and_any_case() -> None:
    text = (
        listing()
        .replace("Title:", "**Title:**")
        .replace("Subtitle:", "**Subtitle**:")
        .replace("Keywords:", "KEYWORDS:")
        .replace("Categories:", "categories :")
    )
    assert PARSER.parse(text).subtitle == "A calm guide to keeping bees"


def test_a_value_may_be_on_the_line_below_its_label_and_may_be_quoted() -> None:
    text = listing().replace("Title: Hive Mind", 'Title:\n"Hive Mind"')
    assert PARSER.parse(text).title == "Hive Mind"


def test_bullets_may_be_dashes_stars_dots_or_numbers() -> None:
    text = listing()
    for old, new in (
        ("- beekeeping for beginners", "* beekeeping for beginners"),
        ("- backyard bees", "\u2022 backyard bees"),
        ("- how to start a hive", "1. how to start a hive"),
        ("- honey bee care", "2) honey bee care"),
    ):
        text = text.replace(old, new)
    assert PARSER.parse(text).keywords[:4] == (
        "beekeeping for beginners",
        "backyard bees",
        "how to start a hive",
        "honey bee care",
    )


def test_description_paragraphs_are_kept_and_blank_runs_are_squeezed() -> None:
    first, second = " ".join([SENTENCE] * 5), " ".join([SENTENCE] * 5)
    text = listing().replace(DESCRIPTION, f"{first}   \n\n\n\n{second}\n")
    assert PARSER.parse(text).description == f"{first}\n\n{second}"


def test_two_blank_lines_between_paragraphs_are_squeezed_to_one() -> None:
    first, second = " ".join([SENTENCE] * 5), " ".join([SENTENCE] * 5)
    text = listing().replace(DESCRIPTION, f"{first}\n\n\n{second}")
    assert PARSER.parse(text).description == f"{first}\n\n{second}"


def test_quotes_and_emphasis_around_a_keyword_are_taken_off() -> None:
    text = (
        listing()
        .replace("- backyard bees", '- "backyard bees"')
        .replace("- honey bee care", "- **honey bee care**")
    )
    assert PARSER.parse(text).keywords[1:4:2] == ("backyard bees", "honey bee care")


def test_dashes_in_the_listing_are_rewritten_before_it_is_read() -> None:
    text = listing().replace("Hive Mind", f"Hive {EM} Mind")
    assert PARSER.parse(text).title == "Hive, Mind"


@pytest.mark.parametrize("label", ["Title", "Subtitle", "Description", "Keywords", "Categories"])
def test_a_missing_section_is_named(label: str) -> None:
    text = "\n".join(line for line in listing().split("\n") if not line.startswith(f"{label}:"))
    assert invalid(text) == f"it has no '{label}:'"


def test_every_missing_section_is_named_at_once() -> None:
    assert invalid("Title: Only a title") == (
        "it has no 'Subtitle:', 'Description:', 'Keywords:', 'Categories:'"
    )


def test_a_section_that_appears_twice_is_refused() -> None:
    assert invalid(listing() + "\nTitle: Another") == "it has two 'Title:' sections"


def test_a_title_with_nothing_after_its_label_is_refused() -> None:
    assert (
        invalid(listing().replace("Title: Hive Mind", "Title:"))
        == "title is one line, and this has 0"
    )


def test_a_title_over_two_lines_is_refused() -> None:
    assert invalid(listing().replace("Title: Hive Mind", "Title: Hive\nMind")) == (
        "title is one line, and this has 2"
    )


def test_a_line_under_keywords_that_is_not_a_bullet_is_refused() -> None:
    assert invalid(listing().replace("- backyard bees", "backyard bees")) == (
        "every line under Keywords: is a bullet point, and 'backyard bees' is not"
    )


def test_the_listing_rules_are_the_models_and_their_reason_is_passed_on() -> None:
    assert invalid(listing().replace(DESCRIPTION, "Too short.")) == (
        "the description has 2 words; a listing needs at least 80"
    )
    assert "exactly 7 keywords, not 6" in invalid(listing().replace("- hobby beekeeping\n", ""))
    assert "not a browse path" in invalid(
        listing().replace("Books > Science & Math > Biological Sciences", "Science")
    )
