# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""TomlSkillWriter: a skill written as a file reads back as exactly that skill, the same bytes every time."""

import hashlib

from engineering_influence.infrastructure.skills.toml_skill_parser import TomlSkillParser
from engineering_influence.infrastructure.skills.toml_skill_writer import TomlSkillWriter
from engineering_influence.interfaces.skill_writer_interface import SkillWriterInterface
from engineering_influence.models.skill import Skill

NASTY = 'Say "why", not \\ how.\nLine two\twith a tab, résumé, “quotes”, 😀.\nLast line.'


def skill(**changes: object) -> Skill:
    fields: dict[str, object] = {
        "name": "plain_style",
        "version": 2,
        "parts": (("outline", NASTY), ("research", "Say where you read it.")),
        "description": 'Short, "plain" sentences.',
    }
    return Skill(**{**fields, **changes})  # type: ignore[arg-type]


def test_it_is_a_skill_writer() -> None:
    assert isinstance(TomlSkillWriter(), SkillWriterInterface)


def test_a_skill_reads_back_as_exactly_that_skill() -> None:
    made = skill()
    assert TomlSkillParser().parse(TomlSkillWriter().render(made), "plain_style") == made


def test_text_with_quotes_backslashes_newlines_and_unicode_survives() -> None:
    back = TomlSkillParser().parse(TomlSkillWriter().render(skill()), "plain_style")
    assert back.part("outline") == NASTY


def test_the_layout_is_fixed_and_the_bytes_are_the_same_every_time() -> None:
    first = TomlSkillWriter().render(skill())
    assert first == TomlSkillWriter().render(skill())
    lines = first.decode("utf-8").split("\n")
    assert lines[:4] == [
        'name = "plain_style"',
        "version = 2",
        'description = "Short, \\"plain\\" sentences."',
        "",
    ]
    assert lines[4] == "[parts]" and lines[5].startswith("outline = ")
    assert first.endswith(b"\n") and not first.endswith(b"\n\n")
    assert (
        hashlib.sha256(first).hexdigest()
        == hashlib.sha256(TomlSkillWriter().render(skill())).hexdigest()
    )


def test_an_empty_description_is_left_out() -> None:
    text = TomlSkillWriter().render(skill(description="")).decode("utf-8")
    assert "description" not in text and text.startswith(
        'name = "plain_style"\nversion = 2\n\n[parts]\n'
    )
    assert TomlSkillParser().parse(text.encode(), "plain_style").description == ""


def test_control_characters_are_written_as_escapes_never_raw() -> None:
    made = skill(parts=(("outline", "a\tb\nc"),))
    text = TomlSkillWriter().render(made).decode("utf-8")
    assert 'outline = "a\\u0009b\\u000ac"' in text
    assert TomlSkillParser().parse(text.encode(), "plain_style") == made
