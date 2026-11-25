# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""Reference sections on a Skill, and the tools a Guidance asks for."""

from typing import Any

import pytest

from engineering_influence.models.guidance import Guidance
from engineering_influence.models.skill import Skill


def skill(**changes: Any) -> Skill:
    fields: dict[str, Any] = {
        "name": "ref_skill",
        "version": 1,
        "parts": (),
        "sections": (("Source Evaluation", "Use SIFT."), ("Database Searching", "Use Boolean.")),
    }
    return Skill(**{**fields, **changes})


def refused(**changes: Any) -> str:
    with pytest.raises((ValueError, TypeError)) as error:
        skill(**changes)
    return str(error.value)


def test_a_skill_may_be_only_reference_sections_and_names_no_stage() -> None:
    made = skill()
    assert made.parts == () and made.stages() == ()
    assert made.section_titles() == ("Source Evaluation", "Database Searching")
    assert made.section("Source Evaluation") == "Use SIFT."


def test_a_skill_may_have_parts_and_sections_together() -> None:
    made = skill(parts=(("research", "Cite it."),))
    assert made.part("research") == "Cite it." and len(made.sections) == 2


def test_a_skill_needs_a_part_or_a_section_and_both_are_tuples() -> None:
    assert (
        refused(parts=(), sections=()) == "a skill needs at least one part or one reference section"
    )
    assert refused(sections=[("T", "x")]) == "parts and sections are tuples"


def test_a_section_is_found_by_its_exact_title_only() -> None:
    made = skill()
    assert made.section("source evaluation") is None
    assert made.section("Missing") is None


def test_a_section_is_a_title_and_its_text() -> None:
    for bad in (("T",), ["T", "x"], "ab", ("a", "b", "c")):
        assert refused(sections=(bad,)) == "a reference section is a (title, text) pair"


@pytest.mark.parametrize(
    "title", ["", "  ", " padded", "padded ", "two\nlines", "a<b", "a>b", "x" * 101]
)
def test_a_title_is_one_plain_line_with_no_angle_brackets_and_at_most_a_hundred_characters(
    title: str,
) -> None:
    assert "one line of at most 100 characters, with no angle brackets" in refused(
        sections=((title, "text"),)
    )


def test_a_title_may_be_exactly_a_hundred_characters_and_may_have_odd_punctuation() -> None:
    assert skill(sections=(("x" * 100, "text"),))
    assert skill(sections=(('Q&A: "CRAAP" / SIFT (2)', "text"),))


def test_a_title_a_person_cannot_see_is_refused() -> None:
    assert "a section title has a character that cannot be seen" in refused(
        sections=(("a" + chr(0x200B) + "b", "text"),)
    )


def test_a_sections_text_is_plain_and_at_most_twenty_thousand_characters() -> None:
    assert refused(sections=(("T", "  "),)) == "the section 'T' needs text"
    assert refused(sections=(("T", 3),)) == "the section 'T' needs text"
    assert skill(sections=(("T", "x" * 20_000),))
    assert "longer than 20000 characters" in refused(sections=(("T", "x" * 20_001),))
    assert "cannot be seen" in refused(sections=(("T", "a" + chr(0x202E)),))


def test_at_most_sixty_four_sections_and_two_hundred_thousand_characters_in_all() -> None:
    sixty_four = tuple((f"S{n}", "x") for n in range(64))
    assert len(skill(sections=sixty_four).sections) == 64
    assert "at most 64 reference sections" in refused(sections=(*sixty_four, ("S64", "x")))
    ten = tuple((f"Big{n}", "x" * 20_000) for n in range(10))
    assert skill(sections=ten)
    assert "hold 200001 characters; the most is 200000" in refused(sections=(*ten, ("One", "y")))


def test_titles_differ_ignoring_case() -> None:
    assert (
        refused(sections=(("Same", "a"), ("same", "b"))) == "section titles differ, ignoring case"
    )


def test_guidance_names_the_tools_its_text_refers_to() -> None:
    made = Guidance("text", "id", ("read_skill",))
    assert made.tools == ("read_skill",) and Guidance().tools == ()
    assert Guidance("text", "id").tools == ()


@pytest.mark.parametrize("bad", [["read_skill"], ("Read",), ("1x",), ("",), (3,), ("a", "a")])
def test_guidance_tools_are_a_tuple_of_distinct_tool_names(bad: Any) -> None:
    with pytest.raises(ValueError, match="tuple of tool names|each tool once"):
        Guidance("text", "id", bad)


def test_guidance_with_no_text_needs_no_tools() -> None:
    with pytest.raises(ValueError, match="needs no tools"):
        Guidance("", "", ("read_skill",))
