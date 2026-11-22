# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""TomlPluginIndexParser: an index is read strictly and can carry an address and a hash, nothing else."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.plugins.toml_plugin_index_parser import (
    TomlPluginIndexParser,
)
from engineering_influence.interfaces.plugin_index_parser_interface import (
    PluginIndexParserInterface,
)
from engineering_influence.models.plugin_index import PluginIndex

A, B = "a" * 64, "b" * 64


def listing(name: str = "research_pack", **changes: str) -> str:
    fields = {
        "name": f'"{name}"',
        "version": "1",
        "description": '"Sources and style."',
        "url": f'"https://plugins.example.com/{name}.toml"',
        "sha256": f'"{A}"',
    }
    given = {**fields, **changes}
    return "[[plugin]]\n" + "".join(f"{key} = {value}\n" for key, value in given.items()) + "\n"


def parse(text: str | bytes) -> PluginIndex:
    return TomlPluginIndexParser().parse(text if isinstance(text, bytes) else text.encode("utf-8"))


def refused(text: str | bytes) -> str:
    with pytest.raises(ApplicationError) as error:
        parse(text)
    assert error.value.code == "PLUGIN_INDEX_INVALID" and error.value.http_status == 422
    assert error.value.message.startswith("plugin index: ")
    return error.value.message


def test_it_is_a_plugin_index_parser() -> None:
    assert isinstance(TomlPluginIndexParser(), PluginIndexParserInterface)


def test_an_index_is_read_with_its_entries_in_name_order() -> None:
    made = parse("version = 1\n\n" + listing("zed_one", sha256=f'"{B}"') + listing("alpha_one"))
    assert [e.name for e in made.entries] == ["alpha_one", "zed_one"]
    zed = made.find("zed_one")
    assert zed is not None
    assert (zed.version, zed.sha256, zed.url, zed.description) == (
        1,
        B,
        "https://plugins.example.com/zed_one.toml",
        "Sources and style.",
    )


def test_an_index_with_no_plugins_is_valid_and_a_description_is_optional() -> None:
    assert parse("version = 1\n").entries == ()
    text = (
        "version = 1\n[[plugin]]\nname = 'a_one'\nversion = 1\nurl = 'https://x.example/a.toml'\n"
    )
    made = parse(text + f"sha256 = '{A}'\n")
    assert made.entries[0].description == ""


def test_bytes_that_are_not_utf8_or_not_toml_are_refused() -> None:
    assert "not UTF-8 text" in refused(b"\xff\xfe version = 1")
    assert "it is not valid TOML: " in refused("version = ")


def test_the_version_must_be_the_one_this_reads() -> None:
    for text in ("", "version = 2\n", 'version = "1"\n', "version = true\n"):
        assert "this reads 1" in refused(text)


def test_an_unknown_top_level_key_is_refused_and_named() -> None:
    assert "unknown top-level key 'extra'" in refused("version = 1\nextra = 1\n")
    assert "unknown top-level key 'name'" in refused('version = 1\nname = "market"\n')


def test_plugin_entries_must_be_a_list_of_tables() -> None:
    assert "[[plugin]] tables" in refused("version = 1\n[plugin]\nname = 'x'\n")
    assert "plugin #1 (?) is not a table" in refused("version = 1\nplugin = [1]\n")


def test_an_entry_can_carry_nothing_but_an_address_and_a_hash() -> None:
    for extra in ('command = "sh"', 'skill = "x"', 'grants = ["research"]', 'stages = ["outline"]'):
        message = refused("version = 1\n" + listing(**{extra.split(" =")[0]: '"x"'}))
        assert "plugin #1 (research_pack) has an unknown key" in message


def test_an_entry_missing_something_is_refused_and_named() -> None:
    for key in ("name", "version", "url", "sha256"):
        text = "version = 1\n[[plugin]]\n" + "".join(
            f"{k} = {v}\n"
            for k, v in {
                "name": "'a_one'",
                "version": "1",
                "url": "'https://x.example/a.toml'",
                "sha256": f"'{A}'",
            }.items()
            if k != key
        )
        assert f"is missing '{key}'" in refused(text)


def test_what_the_model_refuses_is_an_error_that_names_the_entry() -> None:
    cases = {
        "url": ('"http://plugins.example.com/x.toml"', "address that is not usable"),
        "sha256": ('"abc"', "64 lowercase hex"),
        "version": ('"1"', "version that is not a whole number"),
        "description": ("3", "one short line"),
    }
    for key, (value, expected) in cases.items():
        message = refused("version = 1\n" + listing(**{key: value}))
        assert expected in message and "plugin #1 (research_pack)" in message
    message = refused("version = 1\n" + listing("Pack"))
    assert "listed plugin's name" in message and "plugin #1 (Pack)" in message


def test_a_plugin_listed_twice_is_refused() -> None:
    assert "once, in name order" in refused("version = 1\n" + listing() + listing())
