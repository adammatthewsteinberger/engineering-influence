# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""SkillDocument and SkillImportResult: a SKILL.md cut into sections, and what importing one produced."""

from typing import Any

import pytest

from engineering_influence.models.interfaces.skill_document_interface import (
    SkillDocumentInterface,
)
from engineering_influence.models.interfaces.skill_import_result_interface import (
    SkillImportResultInterface,
)
from engineering_influence.models.skill import Skill
from engineering_influence.models.skill_document import SkillDocument
from engineering_influence.models.skill_import_result import SkillImportResult


def document(**changes: Any) -> SkillDocument:
    fields: dict[str, Any] = {
        "name": "research-methodology",
        "description": "A reference.",
        "sections": (("Source Evaluation", "Use CRAAP."), ("Database Searching", "Use Boolean.")),
        "ignored": ("domains",),
    }
    return SkillDocument(**{**fields, **changes})


def refused(**changes: Any) -> str:
    with pytest.raises((ValueError, TypeError)) as error:
        document(**changes)
    return str(error.value)


def test_a_document_has_a_name_a_description_sections_and_the_keys_set_aside() -> None:
    made = document()
    assert isinstance(made, SkillDocumentInterface)
    assert made.titles() == ("Source Evaluation", "Database Searching")
    assert made.ignored == ("domains",)


def test_a_section_is_found_by_title_ignoring_case() -> None:
    made = document()
    assert made.section("source evaluation") == "Use CRAAP."
    assert made.section("DATABASE SEARCHING") == "Use Boolean."
    assert made.section("Missing") is None


@pytest.mark.parametrize("field", ["name", "description"])
def test_the_name_and_description_are_one_line_of_text(field: str) -> None:
    for bad in ("", "  ", "two\nlines", 3):
        assert refused(**{field: bad}) == f"a skill document has a one-line {field}"


def test_it_has_sections_each_with_a_one_line_title_and_text() -> None:
    assert refused(sections=()) == "a skill document has at least one section"
    assert refused(sections=[("T", "x")]) == "a skill document has at least one section"
    assert refused(sections=(("T",),)) == "a section is a (title, text) pair"
    assert refused(sections=(("", "x"),)) == "a section has a one-line title"
    assert refused(sections=(("a\nb", "x"),)) == "a section has a one-line title"
    assert refused(sections=(("T", " "),)) == "the section 'T' has text"


def test_titles_differ_ignoring_case_and_the_ignored_keys_are_a_tuple() -> None:
    assert (
        refused(sections=(("Same", "a"), ("same", "b"))) == "section titles differ, ignoring case"
    )
    assert refused(ignored=["x"]) == "the ignored keys are a tuple"


def test_an_import_result_names_the_skill_the_file_the_sections_and_what_was_set_aside() -> None:
    skill = Skill("a_skill", 1, (("research", "text"),))
    made = SkillImportResult(skill, "a_skill.toml", ("One",), ("domains",), False)
    assert isinstance(made, SkillImportResultInterface)
    assert (made.path, made.sections, made.ignored) == ("a_skill.toml", ("One",), ("domains",))
    for path, sections in (("", ("One",)), (" ", ("One",)), ("a.toml", ())):
        with pytest.raises(ValueError, match="wrote a file and used at least one section"):
            SkillImportResult(skill, path, sections, (), False)
