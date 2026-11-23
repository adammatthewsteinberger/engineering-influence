# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""A skill file with a [reference] table: read strictly, written the same way every time."""

from types import MappingProxyType

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.skills.toml_skill_parser import TomlSkillParser
from engineering_influence.infrastructure.skills.toml_skill_writer import TomlSkillWriter
from engineering_influence.models.skill import Skill

PARSER, WRITER = TomlSkillParser(), TomlSkillWriter()
FILE = b"""name = "research_methodology"
version = 3
description = "A reference."

[parts]
research = "Cite it."

[reference]
"Source Evaluation" = "Use SIFT."
"Database Searching" = "Use Boolean."
"""


def refused(text: str) -> str:
    with pytest.raises(ApplicationError) as error:
        PARSER.parse(text.encode(), "research_methodology")
    assert error.value.code == "SKILL_INVALID"
    return error.value.message


def test_a_reference_table_is_read_in_file_order_next_to_the_parts() -> None:
    made = PARSER.parse(FILE, "research_methodology")
    assert made.part("research") == "Cite it."
    assert made.sections == (
        ("Source Evaluation", "Use SIFT."),
        ("Database Searching", "Use Boolean."),
    )


def test_a_skill_may_be_only_a_reference_table() -> None:
    made = PARSER.parse(b'name = "x"\nversion = 1\n[reference]\nOne = "text"\n', "x")
    assert made.parts == () and made.sections == (("One", "text"),)


def test_a_reference_that_is_not_a_table_of_text_is_refused() -> None:
    base = 'name = "research_methodology"\nversion = 1\n'
    assert "its reference is a table of title = text" in refused(base + 'reference = ["a"]\n')
    assert "its reference is a table of title = text" in refused(base + "[reference]\nOne = 3\n")


def test_a_skill_with_no_parts_and_no_reference_is_refused() -> None:
    assert "at least one part or one reference section" in refused(
        'name = "research_methodology"\nversion = 1\n'
    )


def test_the_rules_of_a_section_apply_when_reading_a_file() -> None:
    base = 'name = "research_methodology"\nversion = 1\n[reference]\n'
    assert "angle brackets" in refused(base + '"a<b" = "text"\n')
    assert "cannot be seen" in refused(base + '"One" = "a\\u200bb"\n')
    assert "needs text" in refused(base + 'One = "  "\n')


def test_a_table_read_from_a_plugin_bundle_may_have_a_reference_too() -> None:
    table = MappingProxyType({"name": "x", "version": 1, "reference": {"One": "text"}})
    assert PARSER.table(table, "x").sections == (("One", "text"),)


def test_what_is_written_reads_back_as_the_same_skill() -> None:
    made = Skill(
        "research_methodology",
        3,
        (("research", "Cite it."),),
        "A reference.",
        (("Source Evaluation", "Use SIFT.\nLine two."), ('Q&A "quoted" \\ slash é', "text")),
    )
    assert PARSER.parse(WRITER.render(made), made.name) == made
    assert WRITER.render(made) == WRITER.render(made)


def test_a_reference_only_skill_is_written_with_no_parts_table() -> None:
    made = Skill("only_ref", 1, (), sections=(("One", "text"),))
    text = WRITER.render(made).decode()
    assert "[parts]" not in text and '[reference]\n"One" = "text"' in text
    assert PARSER.parse(text.encode(), "only_ref") == made


def test_a_skill_with_no_sections_is_written_with_no_reference_table() -> None:
    text = WRITER.render(Skill("plain", 1, (("brief", "x"),))).decode()
    assert "[reference]" not in text and "[parts]" in text
