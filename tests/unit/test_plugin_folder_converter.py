# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""PluginFolderConverter keeps what the locks would accept and names, with the reason, everything it leaves out."""

from collections.abc import Mapping
from typing import Any

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.plugin_folder import PluginFolder
from engineering_influence.services.interfaces.plugin_folder_converter_interface import (
    PluginFolderConverterInterface,
)
from engineering_influence.services.plugin_folder_converter import PluginFolderConverter
from engineering_influence.services.skill_converter import SkillConverter
from engineering_influence.services.skill_markdown_parser import SkillMarkdownParser

CONVERTER = PluginFolderConverter(SkillMarkdownParser(), SkillConverter())

SKILL = "---\nname: {name}\ndescription: About {name}.\n---\n\n## Part\n\nText of {name}."


def skill(name: str) -> tuple[str, str]:
    return (name, SKILL.format(name=name))


def folder(
    servers: Mapping[str, Any] | None = None,
    skills: tuple[tuple[str, str], ...] = (),
    name: str = "my-plugin",
    description: str = "",
    set_aside: tuple[str, ...] = (),
) -> PluginFolder:
    return PluginFolder(name, description, servers or {}, skills, set_aside)


def refused(made: PluginFolder, name: str | None = None, version: int = 1) -> ApplicationError:
    with pytest.raises(ApplicationError) as error:
        CONVERTER.convert(made, name, version)
    assert error.value.http_status == 422
    return error.value


def test_it_is_a_converter() -> None:
    assert isinstance(CONVERTER, PluginFolderConverterInterface)


# -------------------------------------------------------------------------------- skills
def test_each_skill_becomes_a_reference_skill_enabled_for_no_stage() -> None:
    made = CONVERTER.convert(folder(skills=(skill("zeta-one"), skill("alpha"))), None, 2)
    assert made.plugin.identifier() == "my_plugin@2"
    assert made.plugin.skill_names() == ("alpha", "zeta_one")
    for each in made.plugin.skills:
        assert each.parts == () and each.section_titles() == ("Part",)
    assert made.skipped == () and made.notes == ()


def test_a_skill_that_cannot_be_converted_is_skipped_with_the_reason_and_the_rest_stay() -> None:
    made = CONVERTER.convert(
        folder(skills=(skill("good"), ("bad", "no frontmatter at all"))), None, 1
    )
    assert made.plugin.skill_names() == ("good",)
    assert [what for what, _ in made.skipped] == ["skill bad"]
    assert made.skipped[0][1]


def test_a_skill_whose_name_is_already_taken_is_skipped() -> None:
    made = CONVERTER.convert(
        folder(skills=(skill("same"), ("other", SKILL.format(name="same")))), None, 1
    )
    assert made.plugin.skill_names() == ("same",)
    assert made.skipped == (("skill other", "another skill is already named 'same'"),)


def test_a_bundle_holds_sixteen_skills_and_the_rest_are_named() -> None:
    skills = tuple(skill(f"s{number:02d}") for number in range(17))
    made = CONVERTER.convert(folder(skills=skills), None, 1)
    assert len(made.plugin.skills) == 16
    assert made.skipped == (("skill s16", "a bundle holds at most 16 skills"),)


# ------------------------------------------------------------------------------- servers
def test_a_command_with_an_absolute_executable_is_kept_with_only_the_names_of_its_variables() -> (
    None
):
    made = CONVERTER.convert(
        folder(
            {
                "My_Search": {
                    "command": "/opt/bin/searx",
                    "args": ["--port", "1"],
                    "env": {"B": "secret", "A": "x"},
                }
            }
        ),
        None,
        1,
    )
    (server,) = made.plugin.servers
    assert (server.name, server.command, server.env) == (
        "my-search",
        ("/opt/bin/searx", "--port", "1"),
        ("A", "B"),
    )
    assert made.notes == (
        "server my-search: environment values were not copied; ei passes the variables A, B from your environment",
    )


def test_an_explicit_stdio_type_and_no_args_or_env_are_fine() -> None:
    made = CONVERTER.convert(folder({"s": {"type": "stdio", "command": "/bin/x"}}), None, 1)
    assert made.plugin.servers[0].command == ("/bin/x",) and made.notes == ()


def test_a_launcher_is_skipped_and_the_reason_says_why() -> None:
    made = CONVERTER.convert(
        folder({"a": {"command": "npx", "args": ["-y", "x"]}, "b": {"command": "/bin/x"}}), None, 1
    )
    assert made.plugin.server_names() == ("b",)
    assert made.skipped[0][0] == "server a"
    assert "absolute path" in made.skipped[0][1]


def test_a_launcher_with_an_absolute_path_is_skipped_too() -> None:
    made = CONVERTER.convert(folder({"a": {"command": "/usr/bin/npx"}}, (skill("k"),)), None, 1)
    assert "cannot be hashed" in made.skipped[0][1]


def test_a_placeholder_in_a_command_is_skipped_and_never_expanded() -> None:
    made = CONVERTER.convert(
        folder(
            {
                "a": {"command": "${CLAUDE_PLUGIN_ROOT}/bin/x"},
                "b": {"command": "/x", "args": ["${HOME}"]},
            },
            (skill("k"),),
        ),
        None,
        1,
    )
    assert [what for what, _ in made.skipped] == ["server a", "server b"]
    assert all("placeholders" in why for _, why in made.skipped)


@pytest.mark.parametrize(
    ("entry", "why"),
    [
        ({"command": "/x", "args": "text"}, "its args are a list"),
        ({"command": "/x", "args": [1]}, "its command and args are text"),
        ({"command": 3}, "its command and args are text"),
        ({"command": "/x", "env": ["A"]}, "its env is a table"),
        (
            {"command": "/x", "type": "sse"},
            "it is 'sse', and only commands and streamable HTTP are read",
        ),
        ({"type": "http"}, "it has neither a command nor an address"),
        ({}, "it has neither a command nor an address"),
        (
            {"url": "https://x.example/mcp", "type": "sse"},
            "it is 'sse', and only commands and streamable HTTP are read",
        ),
        ({"url": 3}, "its url is text and its headers are a table"),
        (
            {"url": "https://x.example/mcp", "headers": []},
            "its url is text and its headers are a table",
        ),
        (
            {"url": "https://x.example/mcp", "headers": {"X-Key": "v"}},
            "it sets headers other than a bearer token read from an environment variable",
        ),
        (
            {"url": "https://x.example/mcp", "headers": {"Authorization": "Bearer literal"}},
            "it sets headers other than a bearer token read from an environment variable",
        ),
        (
            {"url": "https://x.example/mcp", "headers": {"Authorization": 3}},
            "it sets headers other than a bearer token read from an environment variable",
        ),
        (
            {"url": "https://x.example/mcp", "headers": {"X-Key": "Bearer ${NAME}"}},
            "it sets headers other than a bearer token read from an environment variable",
        ),
        ({"url": "http://x.example/mcp"}, "never plain http"),
    ],
)
def test_a_server_that_cannot_be_carried_over_is_skipped_with_the_reason(
    entry: dict[str, Any], why: str
) -> None:
    made = CONVERTER.convert(folder({"srv": entry}, (skill("k"),)), None, 1)
    assert made.plugin.server_names() == ()
    assert made.skipped[0][0] == "server srv"
    assert why in made.skipped[0][1]


def test_an_address_is_kept_and_a_bearer_token_from_the_environment_is_named_not_copied() -> None:
    made = CONVERTER.convert(
        folder(
            {
                "open": {"url": "https://a.example/mcp"},
                "keyed": {
                    "type": "http",
                    "url": "https://b.example/mcp",
                    "headers": {"authorization": "Bearer ${SEARCH_TOKEN}"},
                },
            }
        ),
        None,
        1,
    )
    keyed, open_server = made.plugin.servers  # in name order
    assert (open_server.url, open_server.bearer_env) == ("https://a.example/mcp", "")
    assert (keyed.url, keyed.bearer_env) == ("https://b.example/mcp", "SEARCH_TOKEN")


def test_names_that_collide_once_made_safe_keep_the_first_and_name_the_second() -> None:
    made = CONVERTER.convert(
        folder({"my_srv": {"command": "/x"}, "my srv": {"command": "/y"}}), None, 1
    )
    assert [server.command for server in made.plugin.servers] == [("/y",)]  # "my srv" sorts first
    assert len(made.skipped) == 1 and "already named 'my-srv'" in made.skipped[0][1]


def test_a_bundle_holds_sixteen_servers_and_the_rest_are_named() -> None:
    servers = {f"s{number:02d}": {"command": f"/bin/x{number}"} for number in range(17)}
    made = CONVERTER.convert(folder(servers), None, 1)
    assert len(made.plugin.servers) == 16
    assert made.skipped == (("server s16", "a bundle holds at most 16 servers"),)


# ------------------------------------------------------------------------------ the bundle
def test_nothing_to_carry_over_is_refused_naming_what_was_skipped() -> None:
    error = refused(folder({"a": {"command": "npx"}}, (("bad", "text"),)))
    assert error.code == "PLUGIN_IMPORT_EMPTY"
    assert error.message.startswith("nothing in the folder could be imported; server a: ")
    assert "skill bad: " in error.message


def test_an_empty_folder_is_refused_without_a_list_of_reasons() -> None:
    error = refused(folder())
    assert (error.code, error.message) == (
        "PLUGIN_IMPORT_EMPTY",
        "nothing in the folder could be imported",
    )


def test_the_name_given_wins_and_the_folders_is_made_safe() -> None:
    assert (
        CONVERTER.convert(folder(skills=(skill("a"),), name="My Plugin-2"), None, 1).plugin.name
        == "my_plugin_2"
    )
    assert CONVERTER.convert(folder(skills=(skill("a"),)), "chosen", 1).plugin.name == "chosen"


@pytest.mark.parametrize(("name", "version"), [("1bad", 1), ("@scope/x", 1), ("ok", 0)])
def test_a_name_or_version_the_bundle_cannot_have_is_refused(name: str, version: int) -> None:
    error = refused(folder(skills=(skill("a"),)), name, version)
    assert error.code == "PLUGIN_IMPORT_INVALID"
    assert error.message.startswith("the plugin cannot be imported: ")


def test_the_description_is_one_printable_line_cut_at_a_word() -> None:
    plain = CONVERTER.convert(
        folder(skills=(skill("a"),), description="Line one\n\tline\x00two"), None, 1
    )
    assert plain.plugin.description == "Line one line two"
    long = CONVERTER.convert(folder(skills=(skill("a"),), description="word " * 100), None, 1)
    assert len(long.plugin.description) <= 300 and long.plugin.description.endswith("word...")


def test_what_was_set_aside_is_passed_through() -> None:
    made = CONVERTER.convert(folder(skills=(skill("a"),), set_aside=("hooks: x",)), None, 1)
    assert made.set_aside == ("hooks: x",)


def test_an_environment_name_that_is_not_capital_letters_skips_the_server() -> None:
    made = CONVERTER.convert(
        folder({"s": {"command": "/x", "env": {"lower": "v"}}}, (skill("k"),)), None, 1
    )
    assert made.skipped == (("server s", "server 's' has an env name that is not capital letters"),)
    assert made.notes == ()


def test_a_server_whose_name_cannot_be_made_safe_is_skipped_with_the_reason() -> None:
    made = CONVERTER.convert(folder({"1x": {"command": "/x"}}, (skill("k"),)), None, 1)
    assert made.skipped == (
        ("server 1x", "a server's name is lowercase letters, digits and hyphens, at most 32"),
    )


def test_a_description_of_exactly_the_limit_is_kept_whole() -> None:
    exact = "a" * 300
    assert (
        CONVERTER.convert(
            folder(skills=(skill("a"),), description=exact), None, 1
        ).plugin.description
        == exact
    )


def test_servers_are_in_name_order_even_when_making_the_names_safe_reorders_them() -> None:
    made = CONVERTER.convert(folder({"a0": {"command": "/x"}, "a_c": {"command": "/y"}}), None, 1)
    assert made.plugin.server_names() == ("a-c", "a0")
