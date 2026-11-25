# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ReadSkillTool: one reference section, only when the stage's own prompt lists it."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.tool_interface import ToolInterface
from engineering_influence.models.skill import Skill
from engineering_influence.services.read_skill_tool import ReadSkillTool

REFERENCE = Skill(
    "research_methodology",
    2,
    (),
    sections=(("Source Evaluation", "Use SIFT."), ("Database Searching", "Use Boolean.")),
)
PLAIN = Skill("plain_style", 1, (("outline", "Be brief."),))
INDEX = (
    "- research_methodology: Source Evaluation (9 characters)\n"
    "- research_methodology: Database Searching (12 characters)"
)


def tool(*skills: Skill) -> ReadSkillTool:
    return ReadSkillTool(skills or (REFERENCE, PLAIN))


def args(skill: str = "research_methodology", section: str = "Source Evaluation") -> dict[str, str]:
    return {"skill": skill, "section": section}


def test_it_is_a_tool_named_read_skill_that_takes_a_skill_and_a_section() -> None:
    made = tool()
    assert isinstance(made, ToolInterface)
    definition = made.definition()
    assert definition.name == "read_skill"
    assert definition.check(args()) == ""
    assert definition.check({"skill": "x"}) != ""
    assert definition.check({**args(), "path": "/etc/passwd"}) != ""
    assert definition.check({"skill": 1, "section": "x"}) != ""


def test_it_gives_back_the_text_of_the_named_section() -> None:
    assert tool().invoke(args()) == "Use SIFT."
    assert tool().invoke(args(section="Database Searching")) == "Use Boolean."


def test_a_skill_with_no_reference_sections_cannot_be_read_from() -> None:
    with pytest.raises(ApplicationError) as error:
        tool().invoke(args(skill="plain_style", section="Anything"))
    assert (error.value.code, error.value.http_status) == ("SKILL_NOT_FOUND", 404)
    assert "no installed skill named 'plain_style' has reference sections" in error.value.message


def test_an_unknown_skill_or_section_is_an_error_naming_what_can_be_read() -> None:
    with pytest.raises(ApplicationError) as missing_skill:
        tool().invoke(args(skill="nope"))
    assert missing_skill.value.code == "SKILL_NOT_FOUND"
    with pytest.raises(ApplicationError) as missing_section:
        tool().invoke(args(section="source evaluation"))
    assert (missing_section.value.code, missing_section.value.http_status) == (
        "SKILL_SECTION_NOT_FOUND",
        404,
    )
    assert missing_section.value.message == (
        "skill 'research_methodology' has no section 'source evaluation'; its sections are: "
        "Source Evaluation; Database Searching"
    )


def test_a_call_is_allowed_only_for_a_section_the_stages_prompt_lists() -> None:
    made = tool()
    assert made.refuses(args(), f"some prompt\n{INDEX}\nmore") == ""
    assert made.refuses(args(section="Database Searching"), INDEX) == ""
    reason = made.refuses(args(section="Ethics"), INDEX)
    assert (
        reason == "read_skill only reads a section that the installed guidance for this stage lists"
    )
    assert made.refuses(args(skill="other_skill"), INDEX) == reason
    assert made.refuses(args(), "a prompt with no index at all") == reason


def test_a_listed_title_must_match_exactly_not_just_start_the_same() -> None:
    made = tool()
    assert made.refuses(args(section="Source"), INDEX) != ""
    assert made.refuses(args(section="Source Evaluation (9"), INDEX) != ""
    assert made.refuses(args(skill="research", section="Source Evaluation"), INDEX) != ""


def test_a_result_is_not_counted_as_something_the_model_was_shown() -> None:
    assert tool().shown("Use SIFT.") == ""


def test_the_revision_names_every_reference_section_so_a_changed_skill_is_not_replayed() -> None:
    first = tool().revision()
    assert first == tool().revision() and len(first) == 16
    changed = Skill(
        "research_methodology",
        2,
        (),
        sections=(("Source Evaluation", "Use SIFT!"), ("Database Searching", "Use Boolean.")),
    )
    assert tool(changed, PLAIN).revision() != first
    renamed = Skill(
        "research_methodology",
        3,
        (),
        sections=REFERENCE.sections,
    )
    assert tool(renamed, PLAIN).revision() != first


def test_a_skill_with_no_reference_sections_does_not_change_the_revision() -> None:
    assert tool(REFERENCE).revision() == tool(REFERENCE, PLAIN).revision()


def test_the_revision_does_not_depend_on_the_order_the_skills_were_given_in() -> None:
    other = Skill("another_one", 1, (), sections=(("Only", "text"),))
    assert tool(REFERENCE, other).revision() == tool(other, REFERENCE).revision()
