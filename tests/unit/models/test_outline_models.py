# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ChapterOutline and Outline: one-line texts in bounded numbers, numbered without gaps."""

from typing import Any

import pytest

from engineering_influence.models.chapter_outline import ChapterOutline
from engineering_influence.models.interfaces.chapter_outline_interface import (
    ChapterOutlineInterface,
)
from engineering_influence.models.interfaces.outline_interface import OutlineInterface
from engineering_influence.models.outline import Outline


def chapter(number: int = 1, **changes: Any) -> ChapterOutline:
    fields: dict[str, Any] = {
        "number": number,
        "title": "The Hive",
        "purpose": "Show how a colony works.",
        "beats": ("Workers and drones", "The queen"),
        "claims": ("A colony holds up to 60,000 bees",),
        "leads_to": "From the hive to the apiary.",
    }
    return ChapterOutline(**{**fields, **changes})


# --------------------------------------------------------------------------- ChapterOutline
def test_a_chapter_renders_as_the_lines_a_drafting_prompt_shows() -> None:
    assert chapter().render() == (
        "Chapter 1: The Hive\n"
        "Purpose: Show how a colony works.\n"
        "Beats:\n"
        "- Workers and drones\n"
        "- The queen\n"
        "Claims to source:\n"
        "- A colony holds up to 60,000 bees\n"
        "Leads to: From the hive to the apiary."
    )


def test_a_chapter_with_no_claims_and_no_next_step_renders_without_those_lines() -> None:
    plain = chapter(claims=(), leads_to="")
    assert plain.render() == (
        "Chapter 1: The Hive\nPurpose: Show how a colony works.\nBeats:\n"
        "- Workers and drones\n- The queen"
    )


def test_a_chapter_has_a_title_a_purpose_beats_claims_and_where_it_leads() -> None:
    made = chapter(3)
    assert isinstance(made, ChapterOutlineInterface)
    assert made.heading() == "Chapter 3: The Hive"
    assert chapter(claims=(), leads_to="").claims == () and chapter(leads_to="").leads_to == ""


@pytest.mark.parametrize("number", [0, -1, True, "1", 1.0, None])
def test_a_chapter_number_is_a_whole_number_from_one(number: Any) -> None:
    with pytest.raises(ValueError, match="whole number from 1"):
        chapter(number)


@pytest.mark.parametrize("field", ["title", "purpose"])
def test_a_title_and_a_purpose_are_one_line_of_visible_text(field: str) -> None:
    for bad in ("", "   ", " padded ", "two\nlines", "bell\x07", "tab\there", 5, None):
        with pytest.raises(ValueError, match="needs text|one line of printable text"):
            chapter(**{field: bad})


def test_the_limits_on_each_text_are_exact() -> None:
    assert len(chapter(title="t" * 160).title) == 160
    with pytest.raises(ValueError, match="longer than 160"):
        chapter(title="t" * 161)
    assert len(chapter(purpose="p" * 600).purpose) == 600
    with pytest.raises(ValueError, match="longer than 600"):
        chapter(purpose="p" * 601)
    with pytest.raises(ValueError, match="longer than 600"):
        chapter(beats=("b" * 601,))
    with pytest.raises(ValueError, match="longer than 600"):
        chapter(claims=("c" * 601,))
    with pytest.raises(ValueError, match="longer than 600"):
        chapter(leads_to="l" * 601)


def test_a_chapter_has_one_to_ten_beats_in_a_tuple() -> None:
    assert len(chapter(beats=tuple(f"beat {n}" for n in range(10))).beats) == 10
    for bad in ((), ["a beat"], None):
        with pytest.raises(ValueError, match="at least one beat"):
            chapter(beats=bad)
    with pytest.raises(ValueError, match="at most 10 beats"):
        chapter(beats=tuple(f"beat {n}" for n in range(11)))
    with pytest.raises(ValueError, match="a beat needs text"):
        chapter(beats=("fine", " "))


def test_a_chapter_lists_at_most_twenty_claims_in_a_tuple() -> None:
    assert len(chapter(claims=tuple(f"claim {n}" for n in range(20))).claims) == 20
    with pytest.raises(ValueError, match="at most 20 claims"):
        chapter(claims=tuple(f"claim {n}" for n in range(21)))
    for bad in (["a claim"], None):
        with pytest.raises(ValueError, match="at most 20 claims"):
            chapter(claims=bad)
    with pytest.raises(ValueError, match="a claim needs text"):
        chapter(claims=("",))


# ------------------------------------------------------------------------------------ Outline
def test_an_outline_is_chapters_numbered_from_one_with_no_gaps() -> None:
    made = Outline((chapter(1), chapter(2, title="The Hive Two"), chapter(3, title="Honey")))
    assert isinstance(made, OutlineInterface) and made.count() == 3
    assert made.chapter(2).title == "The Hive Two" and made.chapter(3).title == "Honey"


def test_an_outline_needs_chapters_in_a_tuple() -> None:
    for bad in ((), [chapter(1)], None):
        with pytest.raises(ValueError, match="at least one chapter"):
            Outline(bad)  # type: ignore[arg-type]


@pytest.mark.parametrize("numbers", [(2, 3), (1, 3), (2, 1), (1, 1), (1, 2, 2), (0, 1)])
def test_the_numbering_has_to_be_one_two_three_in_order(numbers: tuple[int, ...]) -> None:
    if 0 in numbers:
        with pytest.raises(ValueError, match="whole number from 1"):
            Outline(tuple(chapter(n) for n in numbers))
    else:
        with pytest.raises(ValueError, match=r"numbered 1 to \d+ in order"):
            Outline(tuple(chapter(n) for n in numbers))


def test_an_outline_has_at_most_fifty_chapters() -> None:
    fifty = tuple(chapter(n) for n in range(1, 51))
    assert Outline(fifty).count() == 50
    with pytest.raises(ValueError, match="at most 50 chapters"):
        Outline((*fifty, chapter(51)))


def test_asking_for_a_chapter_that_is_not_there_is_an_error() -> None:
    made = Outline((chapter(1), chapter(2)))
    for number in (0, 3, -1):
        with pytest.raises(ValueError, match=f"no chapter {number}"):
            made.chapter(number)
