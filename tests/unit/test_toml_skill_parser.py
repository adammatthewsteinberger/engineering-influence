# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""TomlSkillParser: a skill file is read strictly, and a file that is not a skill says why."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.skills.toml_skill_parser import TomlSkillParser
from engineering_influence.interfaces.skill_parser_interface import SkillParserInterface

GOOD = """
name = "plain_style"
version = 2
description = "Short, plain sentences."

[parts]
research = "Say where you read it."
outline = "Prefer short sentences."
"""


def parse(text: str | bytes, name: str = "plain_style"):  # type: ignore[no-untyped-def]
    data = text if isinstance(text, bytes) else text.encode("utf-8")
    return TomlSkillParser().parse(data, name)


def refused(text: str | bytes, name: str = "plain_style") -> ApplicationError:
    with pytest.raises(ApplicationError) as error:
        parse(text, name)
    assert error.value.code == "SKILL_INVALID" and error.value.http_status == 422
    return error.value


def test_it_is_a_skill_parser() -> None:
    assert isinstance(TomlSkillParser(), SkillParserInterface)


def test_a_skill_is_read_with_its_parts_in_stage_order() -> None:
    skill = parse(GOOD)
    assert (skill.name, skill.version, skill.description) == (
        "plain_style",
        2,
        "Short, plain sentences.",
    )
    assert skill.parts == (
        ("outline", "Prefer short sentences."),
        ("research", "Say where you read it."),
    )


def test_a_description_is_optional() -> None:
    skill = parse('name = "x"\nversion = 1\n[parts]\nbrief = "Be brief."\n', "x")
    assert skill.description == ""


def test_a_multi_line_part_keeps_its_lines() -> None:
    skill = parse('name = "x"\nversion = 1\n[parts]\nbrief = """\nLine one.\nLine two."""\n', "x")
    assert skill.part("brief") == "Line one.\nLine two."


def test_bytes_that_are_not_utf8_are_refused() -> None:
    assert "not UTF-8 text" in refused(b"\xff\xfe name = 1").message


def test_text_that_is_not_toml_is_refused_with_the_parsers_reason() -> None:
    message = refused("name = ").message
    assert message.startswith("skill 'plain_style': it is not valid TOML: ")


def test_a_key_that_is_not_part_of_a_skill_is_refused_and_named() -> None:
    error = refused('tools = ["shell"]\n' + GOOD)
    assert "unknown keys ['tools']" in error.message


def test_the_keys_a_skill_cannot_have_include_anything_that_could_run() -> None:
    for extra in ('command = "rm"', 'untrusted = ["x"]', 'tools = ["a"]', 'url = "https://x.y"'):
        text = 'name = "plain_style"\nversion = 1\n' + extra + '\n[parts]\nbrief = "x"\n'
        assert "unknown keys" in refused(text).message


def test_a_file_must_name_itself_the_same_as_its_file() -> None:
    error = refused(GOOD, "other_name")
    assert "names itself 'plain_style', not 'other_name'" in error.message
    assert "names itself None" in refused('version = 1\n[parts]\nbrief = "x"\n').message


def test_a_missing_version_is_named() -> None:
    assert "missing 'version'" in refused('name = "plain_style"\n[parts]\nbrief = "x"\n').message


def test_parts_must_be_a_table_of_text() -> None:
    assert (
        "at least one part or one reference section"
        in refused('name = "plain_style"\nversion = 1\n').message
    )
    assert (
        "table of stage = text"
        in refused('name = "plain_style"\nversion = 1\nparts = ["a"]\n').message
    )
    assert (
        "table of stage = text"
        in refused('name = "plain_style"\nversion = 1\n[parts]\nbrief = 5\n').message
    )


def test_what_the_model_refuses_comes_back_as_a_skill_error() -> None:
    cases = {
        'name = "plain_style"\nversion = "1"\n[parts]\nbrief = "x"\n': "whole number from 1",
        'name = "plain_style"\nversion = 0\n[parts]\nbrief = "x"\n': "whole number from 1",
        'name = "plain_style"\nversion = 1\n[parts]\nBrief = "x"\n': "named for a stage",
        'name = "plain_style"\nversion = 1\n[parts]\nbrief = "  "\n': "needs text",
        'name = "plain_style"\nversion = 1\n[parts]\nbrief = "a\\u200bb"\n': "cannot be seen",
        'name = "plain_style"\nversion = 1\ndescription = 3\n[parts]\nbrief = "x"\n': "description",
        'name = "plain_style"\nversion = 1\n[parts]\n': "at least one part",
    }
    for text, expected in cases.items():
        assert expected in refused(text).message


def test_a_table_that_is_already_read_is_checked_the_same_way_a_file_is() -> None:
    from types import MappingProxyType

    table = MappingProxyType({"name": "x", "version": 1, "parts": {"brief": "Be brief."}})
    skill = TomlSkillParser().table(table, "x")
    assert (skill.name, skill.version, skill.part("brief")) == ("x", 1, "Be brief.")
    for bad, expected in (
        ({"name": "x", "version": 1, "parts": {"brief": "x"}, "tools": ["a"]}, "unknown keys"),
        ({"name": "y", "version": 1, "parts": {"brief": "x"}}, "names itself 'y', not 'x'"),
        ({"name": "x", "version": 1}, "at least one part or one reference section"),
        ({"name": "x", "parts": {"brief": "x"}}, "missing 'version'"),
    ):
        with pytest.raises(ApplicationError, match=expected) as error:
            TomlSkillParser().table(bad, "x")
        assert error.value.code == "SKILL_INVALID"
