# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""TomlPluginParser: a bundle is read strictly, and nothing in it can decide what a model may do."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.plugins.toml_plugin_parser import TomlPluginParser
from engineering_influence.infrastructure.skills.toml_skill_parser import TomlSkillParser
from engineering_influence.interfaces.plugin_parser_interface import PluginParserInterface
from engineering_influence.models.plugin import Plugin

HEAD = 'name = "research_pack"\nversion = 1\ndescription = "Sources and style."\n'
SERVERS = """
[[server]]
name = "files"
command = ["/usr/local/bin/files-server", "/opt/files/server.js"]
env = ["FILES_ROOT"]

[[server]]
name = "docs"
url = "https://mcp.example.com/v1/mcp"
bearer_env = "DOCS_TOKEN"
"""
SKILLS = """
[[skill]]
name = "plain_style"
version = 2
description = "Short, plain sentences."

[skill.parts]
research = "Say where you read it."
outline = "Prefer short chapters."
"""
GOOD = HEAD + SERVERS + SKILLS


def parser() -> TomlPluginParser:
    return TomlPluginParser(TomlSkillParser())


def parse(text: str | bytes, name: str = "research_pack") -> Plugin:
    return parser().parse(text if isinstance(text, bytes) else text.encode("utf-8"), name)


def refused(text: str | bytes, name: str = "research_pack") -> ApplicationError:
    with pytest.raises(ApplicationError) as error:
        parse(text, name)
    assert error.value.code == "PLUGIN_INVALID" and error.value.http_status == 422
    return error.value


def test_it_is_a_plugin_parser() -> None:
    assert isinstance(parser(), PluginParserInterface)


def test_a_bundle_is_read_with_servers_and_skills_in_name_order() -> None:
    made = parse(GOOD)
    assert (made.name, made.version, made.description) == (
        "research_pack",
        1,
        "Sources and style.",
    )
    assert made.server_names() == ("docs", "files")
    assert made.servers[0].tools_add_arguments()[:3] == ("tools", "add", "--bearer-env")
    [skill] = made.skills
    assert skill.identifier() == "plain_style@2"
    assert skill.parts == (
        ("outline", "Prefer short chapters."),
        ("research", "Say where you read it."),
    )


def test_a_bundle_with_only_servers_or_only_skills_is_fine_and_a_description_is_optional() -> None:
    assert parse('name = "research_pack"\nversion = 1\n' + SERVERS).skills == ()
    assert parse('name = "research_pack"\nversion = 1\n' + SKILLS).servers == ()
    assert parse('name = "research_pack"\nversion = 1\n' + SKILLS).description == ""


def test_bytes_that_are_not_utf8_or_not_toml_are_refused() -> None:
    assert "not UTF-8 text" in refused(b"\xff\xfe name = 1").message
    assert refused("name = ").message.startswith("plugin 'research_pack': it is not valid TOML: ")


def test_a_key_that_is_not_part_of_a_plugin_is_refused_and_named() -> None:
    for extra in ('grants = ["research"]', 'stages = ["outline"]', 'command = "sh"'):
        assert "unknown keys" in refused(extra + "\n" + GOOD).message


def test_a_file_must_name_itself_the_same_as_its_file() -> None:
    assert "names itself 'research_pack', not 'other_name'" in refused(GOOD, "other_name").message
    assert "names itself None" in refused("version = 1\n" + SKILLS).message


def test_a_missing_version_or_an_empty_bundle_is_named() -> None:
    assert "missing 'version'" in refused('name = "research_pack"\n' + SKILLS).message
    assert (
        "at least one server or one skill"
        in refused('name = "research_pack"\nversion = 1\n').message
    )


def test_servers_and_skills_must_be_tables() -> None:
    for key in ("server", "skill"):
        text = f'name = "research_pack"\nversion = 1\n{key} = [1]\n'
        assert f"its {key} entries are [[{key}]] tables" in refused(text).message
        text = f'name = "research_pack"\nversion = 1\n[{key}]\nname = "x"\n'
        assert f"its {key} entries are [[{key}]] tables" in refused(text).message


def test_a_server_cannot_carry_a_grant_or_anything_else_unknown() -> None:
    for extra in ('grants = {research = ["read"]}', 'stage = "research"', "allow = true"):
        text = HEAD + SERVERS.replace('name = "docs"', f'name = "docs"\n{extra}')
        message = refused(text).message
        assert "server 'docs' has unknown keys" in message


def test_a_server_the_lock_would_refuse_is_refused_and_named() -> None:
    cases = {
        'name = "docs"\nurl = "http://mcp.example.com/x"': "https",
        'name = "docs"\ncommand = ["/usr/bin/npx", "server"]': "fetches code",
        'name = "docs"\ncommand = ["relative"]': "absolute path",
        'name = "docs"': "a command or an address",
        'name = "docs"\ncommand = "not-a-list"': "expected a list of text",
        'name = "docs"\nurl = "https://x.example/m"\nenv = ["A"]': "takes no env",
        'name = "docs"\ncommand = [1]': "expected a list of text",
        'command = ["/bin/x"]': "a server's name",
    }
    for body, expected in cases.items():
        message = refused(HEAD + f"[[server]]\n{body}\n").message
        assert expected in message and message.startswith("plugin 'research_pack': server ")


def test_a_skill_in_a_bundle_is_held_to_the_rules_of_a_skill_file() -> None:
    cases = {
        '[[skill]]\nname = "plain_style"\nversion = 1\ntools = ["x"]\n[skill.parts]\nbrief = "x"\n': "unknown keys",
        '[[skill]]\nname = "plain_style"\nversion = 1\n[skill.parts]\nbrief = "a\\u200bb"\n': "cannot be seen",
        '[[skill]]\nname = "plain_style"\nversion = 0\n[skill.parts]\nbrief = "x"\n': "whole number",
        '[[skill]]\nname = "plain_style"\nversion = 1\n[skill.parts]\nBrief = "x"\n': "named for a stage",
        '[[skill]]\nname = "plain_style"\nversion = 1\n': "at least one part or one reference section",
    }
    for body, expected in cases.items():
        message = refused(HEAD + body).message
        assert expected in message and message.startswith(
            "plugin 'research_pack': skill 'plain_style'"
        )


def test_a_skill_without_a_name_is_refused() -> None:
    assert (
        "every skill needs a name"
        in refused(HEAD + '[[skill]]\nversion = 1\n[skill.parts]\nbrief = "x"\n').message
    )
    assert "every skill needs a name" in refused(HEAD + "[[skill]]\nname = 3\n").message


def test_a_name_used_twice_or_listed_out_of_order_is_sorted_or_refused() -> None:
    twice = HEAD + SERVERS + SERVERS
    assert "once, in name order" in refused(twice).message
    skill = SKILLS + SKILLS
    assert "once, in name order" in refused(HEAD + skill).message


def test_skills_listed_out_of_order_are_read_in_name_order() -> None:
    def skill(name: str) -> str:
        return f'\n[[skill]]\nname = "{name}"\nversion = 1\n[skill.parts]\nbrief = "Be brief."\n'

    made = parse(HEAD + skill("zed_one") + skill("alpha_one") + skill("mid_one"))
    assert made.skill_names() == ("alpha_one", "mid_one", "zed_one")
