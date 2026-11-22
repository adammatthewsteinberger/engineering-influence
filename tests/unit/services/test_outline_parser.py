# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""OutlineParser: the contract between the outline stage and the drafting stage, read strictly."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.outline import Outline
from engineering_influence.services.interfaces.outline_parser_interface import (
    OutlineParserInterface,
)
from engineering_influence.services.outline_parser import OutlineParser

GOOD = """## Chapter 1: The Hive
Purpose: Show how a colony works.
Beats:
- Workers, drones and the queen
- How a hive keeps its temperature
- What the colony does in winter
Claims to source:
- A colony holds up to 60,000 bees (https://example.org/colony)
Leads to: From the hive to the place it stands.

## Chapter 2: The Apiary
Purpose: Choose where hives go.
Beats:
- Sun, shelter and water
- Distance from neighbours
Claims to source:
Leads to: From the site to the first season.

## Chapter 3: The First Year
Purpose: Get through the first season.
Beats:
- Installing a package
- Feeding
Claims to source:
"""


def parse(text: str) -> Outline:
    return OutlineParser().parse(text)


def refused(text: str) -> str:
    with pytest.raises(ApplicationError) as error:
        parse(text)
    assert (error.value.code, error.value.http_status) == ("OUTLINE_INVALID", 422)
    assert error.value.message.startswith("the outline cannot be read: ")
    return error.value.message


def test_it_is_an_outline_parser() -> None:
    assert isinstance(OutlineParser(), OutlineParserInterface)


def test_the_format_the_stage_is_told_to_write_is_read_chapter_by_chapter() -> None:
    made = parse(GOOD)
    assert made.count() == 3
    first = made.chapter(1)
    assert (first.number, first.title, first.purpose) == (1, "The Hive", "Show how a colony works.")
    assert first.beats == (
        "Workers, drones and the queen",
        "How a hive keeps its temperature",
        "What the colony does in winter",
    )
    assert first.claims == ("A colony holds up to 60,000 bees (https://example.org/colony)",)
    assert first.leads_to == "From the hive to the place it stands."
    second, third = made.chapter(2), made.chapter(3)
    assert second.claims == () and second.leads_to == "From the site to the first season."
    assert third.beats == ("Installing a package", "Feeding") and third.leads_to == ""


def test_text_before_the_first_chapter_is_ignored() -> None:
    made = parse("Sure! Here is the outline you asked for.\n\n# A Title\n\n" + GOOD)
    assert made.count() == 3 and made.chapter(1).title == "The Hive"


def test_a_closing_paragraph_after_a_blank_line_belongs_to_no_chapter() -> None:
    text = GOOD + "\nFront matter: a short foreword. Back matter: a glossary.\n"
    last = parse(text).chapter(3)
    assert last.beats == ("Installing a package", "Feeding")
    assert not any("glossary" in beat for beat in last.beats)
    after_leads = GOOD.replace(
        "Leads to: From the site to the first season.",
        "Leads to: From the site to the first season.\n\nA note on front matter.",
    )
    assert parse(after_leads).chapter(2).leads_to == "From the site to the first season."


@pytest.mark.parametrize(
    "heading",
    [
        "## Chapter 1: The Hive",
        "# Chapter 1: The Hive",
        "### Chapter 1: The Hive",
        "#### Chapter 1: The Hive",
        "## Chapter 1 - The Hive",
        "## Chapter 1 – The Hive",
        "## Chapter 1 — The Hive",
        "## Chapter 1. The Hive",
        "## **Chapter 1: The Hive**",
        "##   chapter   1 :  The Hive  ",
    ],
)
def test_a_heading_may_vary_in_level_punctuation_case_and_bold(heading: str) -> None:
    made = parse(f"{heading}\nPurpose: p\nBeats:\n- b\n")
    assert made.chapter(1).title == "The Hive"


@pytest.mark.parametrize(
    ("purpose", "beats"),
    [
        ("**Purpose:** p", "**Beats:**"),
        ("**Purpose**: p", "**Beats**:"),
        ("PURPOSE: p", "BEATS:"),
        ("purpose:   p", "beats :"),
    ],
)
def test_a_label_may_be_bold_in_any_case(purpose: str, beats: str) -> None:
    made = parse(f"## Chapter 1: T\n{purpose}\n{beats}\n- b one\n")
    assert made.chapter(1).purpose == "p" and made.chapter(1).beats == ("b one",)


@pytest.mark.parametrize(
    "bullet", ["- b one", "* b one", "• b one", "1. b one", "2) b one", "10. b one"]
)
def test_a_bullet_may_be_a_dash_a_star_a_dot_or_a_number(bullet: str) -> None:
    assert parse(f"## Chapter 1: T\nPurpose: p\nBeats:\n{bullet}\n").chapter(1).beats == ("b one",)


def test_a_bullet_that_wraps_keeps_its_words_but_a_blank_line_ends_it() -> None:
    text = "## Chapter 1: T\nPurpose: p\nBeats:\n- a long beat that\n  wraps onto a second line\n- another\n\nstray words\n"
    assert parse(text).chapter(1).beats == ("a long beat that wraps onto a second line", "another")


def test_a_purpose_or_a_leads_to_that_wraps_keeps_its_words() -> None:
    text = "## Chapter 1: T\nPurpose: first half\nsecond half\nBeats:\n- b\nLeads to: goes on\nand on\n"
    made = parse(text).chapter(1)
    assert made.purpose == "first half second half" and made.leads_to == "goes on and on"


def test_a_list_given_on_the_label_line_is_the_first_item() -> None:
    made = parse(
        "## Chapter 1: T\nPurpose: p\nBeats: - first\n- second\nClaims to source: a claim\n"
    )
    assert made.chapter(1).beats == ("first", "second") and made.chapter(1).claims == ("a claim",)


def test_a_line_that_only_starts_like_a_label_is_not_one() -> None:
    text = "## Chapter 1: T\nPurpose: p\nBeats:\n- b\nPurposeful bees and Beats of the wing\n"
    made = parse(text).chapter(1)
    assert made.beats == ("b Purposeful bees and Beats of the wing",) and made.purpose == "p"


def test_a_bullet_outside_a_list_is_not_a_beat() -> None:
    text = "## Chapter 1: T\n- stray bullet\nPurpose: p\nBeats:\n- real\n"
    assert parse(text).chapter(1).beats == ("real",)


def test_text_from_a_model_is_cleaned_to_single_visible_lines() -> None:
    hidden = chr(0x200B) + chr(0x202E) + chr(0x0000)
    text = (
        f"## Chapter 1:   The\t\u00a0Hive{hidden}  \nPurpose:  keep   it\tshort{hidden}\n"
        f"Beats:\n- zero{hidden}width\n"
    )
    made = parse(text).chapter(1)
    assert (
        made.title == "The Hive"
        and made.purpose == "keep it short"
        and made.beats == ("zerowidth",)
    )


def test_a_chapter_with_no_purpose_or_no_beats_is_refused_and_named() -> None:
    assert "chapter 1: the purpose needs text" in refused("## Chapter 1: T\nBeats:\n- b\n")
    assert "chapter 2: a chapter needs at least one beat" in refused(
        "## Chapter 1: T\nPurpose: p\nBeats:\n- b\n## Chapter 2: U\nPurpose: p\nBeats:\n"
    )
    assert "chapter 1: a chapter needs at least one beat" in refused(
        "## Chapter 1: T\nPurpose: p\n"
    )


def test_chapters_that_are_not_numbered_in_order_are_refused() -> None:
    body = "Purpose: p\nBeats:\n- b\n"
    assert "numbered 1 to 2 in order, not [2, 3]" in refused(
        f"## Chapter 2: A\n{body}## Chapter 3: B\n{body}"
    )
    assert "numbered 1 to 2 in order, not [1, 1]" in refused(
        f"## Chapter 1: A\n{body}## Chapter 1: B\n{body}"
    )
    assert "numbered 1 to 2 in order, not [2, 1]" in refused(
        f"## Chapter 2: A\n{body}## Chapter 1: B\n{body}"
    )


def test_text_with_no_chapter_heading_is_refused_and_says_what_a_heading_looks_like() -> None:
    for text in ("", "   \n\n", "Just a paragraph about bees.", "1. Chapter one\n2. Chapter two\n"):
        assert (
            "no chapters; each chapter starts with a heading like '## Chapter 1: Title'"
            in refused(text)
        )


def test_too_many_chapters_are_refused() -> None:
    body = "Purpose: p\nBeats:\n- b\n"
    fifty = "".join(f"## Chapter {n}: T{n}\n{body}" for n in range(1, 51))
    assert parse(fifty).count() == 50
    assert "at most 50 chapters" in refused(fifty + f"## Chapter 51: T\n{body}")


def test_a_text_that_is_too_long_is_refused_and_names_the_chapter() -> None:
    message = refused(f"## Chapter 1: {'t' * 161}\nPurpose: p\nBeats:\n- b\n")
    assert "chapter 1: the title is longer than 160 characters" in message
    assert "chapter 1: a beat is longer than 600" in refused(
        f"## Chapter 1: T\nPurpose: p\nBeats:\n- {'b' * 601}\n"
    )


def test_the_parser_reads_the_same_text_the_same_way_every_time() -> None:
    assert parse(GOOD) == parse(GOOD)


def test_a_line_separator_inside_a_line_is_a_line_break_and_loses_no_words() -> None:
    separator = chr(0x2028)
    text = f"## Chapter 1: T\nPurpose: p\nBeats:\n- zero{separator}width\n"
    assert parse(text).chapter(1).beats == ("zero width",)


@pytest.mark.parametrize("code_point", [0xD800, 0xE000, 0x0378, 0x0007, 0x2060, 0xFEFF])
def test_every_kind_of_hidden_character_is_removed_from_a_beat(code_point: int) -> None:
    text = f"## Chapter 1: T\nPurpose: p\nBeats:\n- zero{chr(code_point)}width\n"
    assert parse(text).chapter(1).beats == ("zerowidth",)


def test_words_right_after_an_empty_list_label_belong_to_no_beat() -> None:
    text = "## Chapter 1: T\nPurpose: p\nBeats:\nstray words\n- real\nClaims to source:\nmore stray words\n"
    made = parse(text).chapter(1)
    assert made.beats == ("real",) and made.claims == ()


def test_a_bullet_right_after_a_heading_does_not_join_the_list_of_the_chapter_before() -> None:
    text = (
        "## Chapter 1: A\nPurpose: p\nBeats:\n- first beat\nClaims to source:\n- first claim\n"
        "## Chapter 2: B\n- stray bullet\nPurpose: q\nBeats:\n- second beat\n"
    )
    made = parse(text)
    assert made.chapter(1).claims == ("first claim",)
    assert made.chapter(2).claims == () and made.chapter(2).beats == ("second beat",)


def test_a_label_before_the_first_chapter_belongs_to_no_chapter() -> None:
    text = "Purpose: this outline is for beekeepers\nBeats:\n- a preamble bullet\n\n" + GOOD
    made = parse(text)
    assert made.count() == 3 and made.chapter(1).purpose == "Show how a colony works."
    assert "preamble" not in " ".join(made.chapter(1).beats)
