# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""PluginIndexEntry, PluginIndex and PluginDownload: an index is a promise about bytes, and nothing else."""

from pathlib import Path
from typing import Any

import pytest

from engineering_influence.models.interfaces.plugin_download_interface import (
    PluginDownloadInterface,
)
from engineering_influence.models.interfaces.plugin_index_entry_interface import (
    PluginIndexEntryInterface,
)
from engineering_influence.models.interfaces.plugin_index_interface import PluginIndexInterface
from engineering_influence.models.plugin import Plugin
from engineering_influence.models.plugin_bundle import PluginBundle
from engineering_influence.models.plugin_download import PluginDownload
from engineering_influence.models.plugin_index import PluginIndex
from engineering_influence.models.plugin_index_entry import PluginIndexEntry
from engineering_influence.models.skill import Skill

A = "a" * 64
URL = "https://plugins.example.com/research_pack.toml"


def entry(name: str = "research_pack", **changes: Any) -> PluginIndexEntry:
    fields: dict[str, Any] = {
        "name": name,
        "version": 1,
        "url": URL,
        "sha256": A,
        "description": "Sources and style for research.",
    }
    return PluginIndexEntry(**{**fields, **changes})


# --------------------------------------------------------------------------- PluginIndexEntry
def test_an_entry_is_a_name_a_version_an_address_and_a_hash() -> None:
    made = entry()
    assert isinstance(made, PluginIndexEntryInterface) and made.identifier() == "research_pack@1"
    assert entry(description="").description == ""


@pytest.mark.parametrize("name", ["", "Pack", "a-b", "1x", 3, None])
def test_an_entry_name_is_a_plugin_name(name: Any) -> None:
    with pytest.raises(ValueError, match="listed plugin's name"):
        entry(name=name)


@pytest.mark.parametrize("version", [0, True, "1", 1.0, None])
def test_an_entry_version_is_a_whole_number_from_one(version: Any) -> None:
    with pytest.raises(ValueError, match="version that is not a whole number"):
        entry(version=version)


@pytest.mark.parametrize("digest", ["a" * 63, "A" * 64, "g" * 64, "", 5, None])
def test_an_entry_hash_is_64_lowercase_hex_digits(digest: Any) -> None:
    with pytest.raises(ValueError, match="64 lowercase hex"):
        entry(sha256=digest)


def test_a_description_is_one_short_line_of_printable_text() -> None:
    assert len(entry(description="x" * 300).description) == 300
    for bad in ("x" * 301, "two\nlines", "bell\x07", 5):
        with pytest.raises(ValueError, match="one short line of printable text"):
            entry(description=bad)


@pytest.mark.parametrize(
    "url",
    [
        "",
        "http://plugins.example.com/x.toml",
        "https://user:pw@plugins.example.com/x.toml",
        f"{URL}?token=1",
        f"{URL}#frag",
        "https://plugins.example.com/a b.toml",
        "ftp://plugins.example.com/x.toml",
        3,
        None,
    ],
)
def test_an_address_is_https_with_nothing_that_could_carry_a_secret(url: Any) -> None:
    with pytest.raises(ValueError, match="address that is not usable"):
        entry(url=url)


# ------------------------------------------------------------------------------- PluginIndex
def index() -> PluginIndex:
    return PluginIndex(
        (
            entry("alpha_one", description="Sources for research."),
            entry("beta_two", description="House STYLE for chapters."),
            entry("gamma_three", description=""),
        )
    )


def test_an_index_finds_a_plugin_by_name() -> None:
    made = index()
    assert isinstance(made, PluginIndexInterface) and PluginIndex.VERSION == 1
    found = made.find("beta_two")
    assert found is not None and found.name == "beta_two"
    assert made.find("none") is None and PluginIndex().find("alpha_one") is None


def test_searching_matches_name_or_description_ignoring_case() -> None:
    made = index()
    assert [e.name for e in made.search("alpha")] == ["alpha_one"]
    assert [e.name for e in made.search("STYLE")] == ["beta_two"]
    assert [e.name for e in made.search("style")] == ["beta_two"]
    assert [e.name for e in made.search("research")] == ["alpha_one"]
    assert [e.name for e in made.search("_t")] == ["beta_two", "gamma_three"]
    assert made.search("nothing like this") == ()


def test_no_text_or_blank_text_lists_everything_and_the_text_is_trimmed() -> None:
    made = index()
    assert len(made.search("")) == 3 and len(made.search("   ")) == 3
    assert [e.name for e in made.search("  alpha  ")] == ["alpha_one"]


def test_an_index_lists_each_plugin_once_in_name_order() -> None:
    for bad in ((entry("b_one"), entry("a_one")), (entry("a_one"), entry("a_one"))):
        with pytest.raises(ValueError, match="once, in name order"):
            PluginIndex(bad)
    with pytest.raises(TypeError, match="tuple"):
        PluginIndex([entry()])  # type: ignore[arg-type]


def test_an_index_lists_at_most_five_hundred_plugins() -> None:
    entries = tuple(entry(f"p{n:03d}") for n in range(500))
    assert len(PluginIndex(entries).entries) == 500
    with pytest.raises(ValueError, match="at most 500 plugins"):
        PluginIndex((*entries, entry("p500")))


# ----------------------------------------------------------------------------- PluginDownload
def test_a_download_holds_the_entry_the_bundle_and_the_saved_path() -> None:
    plugin = Plugin("research_pack", 1, skills=(Skill("a_one", 1, (("brief", "x"),)),))
    made = PluginDownload(entry(), PluginBundle(plugin, A), Path("/x/research_pack.toml"))
    assert isinstance(made, PluginDownloadInterface)
    assert made.path == Path("/x/research_pack.toml") and made.bundle.sha256 == A
