# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""SkillConverter: the chosen sections become one part per stage, and nothing is cut to fit."""

from typing import Any

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.skill import Skill
from engineering_influence.models.skill_document import SkillDocument
from engineering_influence.services.interfaces.skill_converter_interface import (
    SkillConverterInterface,
)
from engineering_influence.services.skill_converter import SkillConverter

CONVERTER = SkillConverter()
SECTIONS = (
    ("Source Evaluation", "Use CRAAP."),
    ("Database Searching", "Use Boolean."),
    ("Ethics", "Be fair."),
)


def document(**changes: Any) -> SkillDocument:
    fields: dict[str, Any] = {
        "name": "research-methodology",
        "description": "A reference.",
        "sections": SECTIONS,
    }
    return SkillDocument(**{**fields, **changes})


def convert(
    doc: SkillDocument | None = None,
    name: str | None = None,
    version: int = 1,
    stages: tuple[str, ...] = ("research",),
    titles: tuple[str, ...] = (),
) -> Skill:
    return CONVERTER.convert(doc or document(), name, version, stages, titles)


def refused(code: str, **kwargs: Any) -> str:
    with pytest.raises(ApplicationError) as error:
        convert(**kwargs)
    assert (error.value.code, error.value.http_status) == (code, 422)
    return error.value.message


def test_it_is_a_skill_converter() -> None:
    assert isinstance(CONVERTER, SkillConverterInterface)


def test_every_section_is_kept_with_its_heading_when_none_are_chosen() -> None:
    made = convert()
    assert made.parts == (
        (
            "research",
            "## Source Evaluation\n\nUse CRAAP.\n\n## Database Searching\n\nUse Boolean.\n\n## Ethics\n\nBe fair.",
        ),
    )
    assert (made.name, made.version, made.description) == (
        "research_methodology",
        1,
        "A reference.",
    )


def test_chosen_sections_are_kept_in_the_files_order_not_the_order_asked_for() -> None:
    made = convert(titles=("ethics", "SOURCE EVALUATION"))
    assert made.part("research") == "## Source Evaluation\n\nUse CRAAP.\n\n## Ethics\n\nBe fair."
    assert CONVERTER.sections(document(), ("ethics", "SOURCE EVALUATION")) == (
        "Source Evaluation",
        "Ethics",
    )
    assert CONVERTER.sections(document(), ()) == (
        "Source Evaluation",
        "Database Searching",
        "Ethics",
    )


def test_each_named_stage_gets_the_same_text_once_in_stage_order() -> None:
    made = convert(stages=("research", "outline", "research"))
    assert [stage for stage, _ in made.parts] == ["outline", "research"]
    assert made.part("outline") == made.part("research")


def test_a_skill_needs_a_stage_to_speak_to() -> None:
    assert "at least one stage" in refused("SKILL_IMPORT_INVALID", stages=())


def test_a_section_that_is_not_there_is_named_with_the_ones_that_are() -> None:
    message = refused("SKILL_IMPORT_INVALID", titles=("Sourse Evaluation",))
    assert message == (
        "the skill cannot be imported: there is no section 'Sourse Evaluation'; the sections are: "
        "'Source Evaluation'; 'Database Searching'; 'Ethics'"
    )


def test_a_part_may_be_exactly_the_limit_and_not_a_character_more() -> None:
    heading = len("## Big\n\n")
    exact = document(sections=(("Big", "x" * (Skill.MAX_PART_CHARS - heading)),))
    assert len(convert(exact).part("research") or "") == Skill.MAX_PART_CHARS
    over = document(sections=(("Big", "x" * (Skill.MAX_PART_CHARS - heading + 1)),))
    message = refused("SKILL_IMPORT_TOO_LARGE", doc=over)
    assert "the chosen text is 8,001 characters and a part holds at most 8,000" in message
    assert "choose sections with --section" in message and "'Big' 7,993" in message


def test_too_large_lists_every_section_with_its_length_so_the_choice_is_easy() -> None:
    big = document(sections=(("Alpha", "a" * 5000), ("Beta", "b" * 5000), ("Gamma", "c" * 100)))
    message = refused("SKILL_IMPORT_TOO_LARGE", doc=big)
    assert "'Alpha' 5,000; 'Beta' 5,000; 'Gamma' 100" in message
    assert convert(big, titles=("Alpha", "Gamma")).part("research") is not None


@pytest.mark.parametrize(
    ("name", "derived"),
    [
        ("research-methodology", "research_methodology"),
        ("Plain Style", "plain_style"),
        ("  spaced   out  ", "spaced_out"),
        ("a-b c", "a_b_c"),
    ],
)
def test_the_name_is_the_skill_files_made_safe(name: str, derived: str) -> None:
    assert convert(document(name=name)).name == derived


@pytest.mark.parametrize("name", ["1st", "-leading", "café", "dot.ted"])
def test_a_name_that_cannot_be_made_safe_says_to_give_one(name: str) -> None:
    assert "give one with --name" in refused("SKILL_IMPORT_INVALID", doc=document(name=name))


def test_a_name_that_is_given_is_used_and_checked_by_the_skill_model() -> None:
    assert convert(name="my_skill").name == "my_skill"
    assert "lowercase letters" in refused("SKILL_IMPORT_INVALID", name="Bad Name")


def test_the_version_is_the_one_given_and_must_be_valid() -> None:
    assert convert(version=7).version == 7
    assert "whole number from 1" in refused("SKILL_IMPORT_INVALID", version=0)


def test_a_description_at_the_limit_is_kept_and_a_longer_one_is_cut_at_a_word() -> None:
    limit = Skill.MAX_DESCRIPTION_CHARS
    exact = "word " * 59 + "wordy"
    assert len(exact) == limit
    assert convert(document(description=exact)).description == exact
    longer = convert(document(description=exact + "s")).description
    assert longer == ("word " * 59).rstrip() + "..."


def test_a_description_with_no_space_to_cut_at_is_cut_at_the_limit() -> None:
    made = convert(document(description="x" * 400)).description
    assert made == "x" * (Skill.MAX_DESCRIPTION_CHARS - 3) + "..."


def test_text_a_person_could_not_see_is_refused_and_the_character_is_named() -> None:
    hidden = chr(0x200B)
    message = refused("SKILL_IMPORT_INVALID", doc=document(sections=(("T", f"a{hidden}b"),)))
    assert "U+200B" in message and message.startswith("the skill cannot be imported: ")
