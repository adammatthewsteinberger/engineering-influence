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
    reference: bool = False,
) -> Skill:
    return CONVERTER.convert(doc or document(), name, version, stages, titles, reference)


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


# ------------------------------------------------------------------------- reference mode
def test_reference_mode_keeps_each_section_separate_with_no_parts_and_no_stages() -> None:
    made = convert(stages=(), reference=True)
    assert made.parts == () and made.stages() == ()
    assert made.sections == SECTIONS
    assert made.name == "research_methodology"


def test_reference_mode_keeps_only_the_chosen_sections_in_the_files_order() -> None:
    made = convert(stages=(), titles=("ethics", "source evaluation"), reference=True)
    assert made.sections == (("Source Evaluation", "Use CRAAP."), ("Ethics", "Be fair."))


def test_a_reference_skill_is_not_tied_to_stages_so_naming_one_is_refused() -> None:
    message = refused("SKILL_IMPORT_INVALID", stages=("research",), reference=True)
    assert message == (
        "the skill cannot be imported: a reference skill is read on request and is not tied to "
        "stages; leave out --stage and enable it for the stages that should read it"
    )


def test_a_reference_section_may_be_far_longer_than_a_part_up_to_twenty_thousand() -> None:
    big = document(sections=(("Long", "x" * 15_000), ("Exact", "y" * 20_000)))
    assert [len(text) for _, text in convert(big, stages=(), reference=True).sections] == [
        15_000,
        20_000,
    ]


def test_a_reference_section_over_twenty_thousand_is_named_with_its_length() -> None:
    big = document(sections=(("Fine", "x" * 100), ("Huge", "y" * 20_001), ("Huger", "z" * 30_000)))
    message = refused("SKILL_IMPORT_TOO_LARGE", doc=big, stages=(), reference=True)
    assert message == (
        "a reference section holds at most 20,000 characters, and 'Huge' has 20,001; 'Huger' has "
        "30,000; leave those out with --section"
    )
    assert convert(big, stages=(), titles=("Fine",), reference=True).sections == (
        ("Fine", "x" * 100),
    )


def test_a_reference_section_with_angle_brackets_in_its_title_is_refused() -> None:
    odd = document(sections=(("Use <untrusted> tags", "text"),))
    assert "angle brackets" in refused("SKILL_IMPORT_INVALID", doc=odd, stages=(), reference=True)


def test_reference_mode_is_refused_for_too_many_sections() -> None:
    many = document(sections=tuple((f"S{n}", "x") for n in range(65)))
    assert "at most 64 reference sections" in refused(
        "SKILL_IMPORT_INVALID", doc=many, stages=(), reference=True
    )


def test_reference_mode_names_a_missing_section_as_part_mode_does() -> None:
    assert "there is no section 'Nope'" in refused(
        "SKILL_IMPORT_INVALID", stages=(), titles=("Nope",), reference=True
    )
