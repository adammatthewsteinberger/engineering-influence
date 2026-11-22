# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""PluginServer, Plugin, PluginLockEntry and PluginLock: a bundle is a definition, bounded and in order."""

from typing import Any

import pytest

from engineering_influence.models.interfaces.plugin_addition_interface import (
    PluginAdditionInterface,
)
from engineering_influence.models.interfaces.plugin_bundle_interface import PluginBundleInterface
from engineering_influence.models.interfaces.plugin_interface import PluginInterface
from engineering_influence.models.interfaces.plugin_lock_entry_interface import (
    PluginLockEntryInterface,
)
from engineering_influence.models.interfaces.plugin_lock_interface import PluginLockInterface
from engineering_influence.models.interfaces.plugin_removal_interface import (
    PluginRemovalInterface,
)
from engineering_influence.models.interfaces.plugin_server_interface import PluginServerInterface
from engineering_influence.models.plugin import Plugin
from engineering_influence.models.plugin_addition import PluginAddition
from engineering_influence.models.plugin_bundle import PluginBundle
from engineering_influence.models.plugin_lock import PluginLock
from engineering_influence.models.plugin_lock_entry import PluginLockEntry
from engineering_influence.models.plugin_removal import PluginRemoval
from engineering_influence.models.plugin_server import PluginServer
from engineering_influence.models.skill import Skill
from engineering_influence.models.skill_lock import SkillLock

A, B = "a" * 64, "b" * 64
URL = "https://mcp.example.com/v1/mcp"


def local(**changes: Any) -> PluginServer:
    fields: dict[str, Any] = {
        "name": "files",
        "command": ("/usr/local/bin/files-server", "/opt/files/server.js"),
        "env": ("FILES_ROOT",),
    }
    return PluginServer(**{**fields, **changes})


def remote(**changes: Any) -> PluginServer:
    return PluginServer(**{"name": "docs", "url": URL, "bearer_env": "DOCS_TOKEN", **changes})


def skill(name: str = "plain_style") -> Skill:
    return Skill(name, 2, (("outline", "Prefer short chapters."),))


def plugin(**changes: Any) -> Plugin:
    fields: dict[str, Any] = {
        "name": "research_pack",
        "version": 1,
        "description": "Sources and style.",
        "servers": (remote(), local()),
        "skills": (skill(),),
    }
    return Plugin(**{**fields, **changes})


def entry(name: str = "research_pack", **changes: Any) -> PluginLockEntry:
    fields: dict[str, Any] = {
        "name": name,
        "version": 1,
        "sha256": A,
        "servers": ("docs", "files"),
        "skills": (("plain_style", B),),
    }
    return PluginLockEntry(**{**fields, **changes})


# ------------------------------------------------------------------------------ PluginServer
def test_a_local_server_says_what_to_type_to_lock_it() -> None:
    made = local()
    assert isinstance(made, PluginServerInterface) and not made.remote()
    assert made.tools_add_arguments() == (
        "tools",
        "add",
        "--env",
        "FILES_ROOT",
        "files",
        "--",
        "/usr/local/bin/files-server",
        "/opt/files/server.js",
    )
    assert local(env=()).tools_add_arguments()[:3] == ("tools", "add", "files")


def test_a_remote_server_says_what_to_type_to_lock_it() -> None:
    made = remote()
    assert made.remote()
    assert made.tools_add_arguments() == (
        "tools",
        "add",
        "--bearer-env",
        "DOCS_TOKEN",
        "--url",
        URL,
        "docs",
    )
    assert remote(bearer_env="").tools_add_arguments() == ("tools", "add", "--url", URL, "docs")


@pytest.mark.parametrize("name", ["", "Docs", "-docs", "x" * 33, "a b", 5, None])
def test_a_server_name_is_what_the_tool_lock_accepts(name: Any) -> None:
    with pytest.raises(ValueError, match="a server's name"):
        remote(name=name)


def test_a_server_has_a_command_or_an_address_and_not_both() -> None:
    with pytest.raises(ValueError, match="a command or an address, and not both"):
        PluginServer("docs")
    with pytest.raises(ValueError, match="a command or an address, and not both"):
        PluginServer("docs", command=("/bin/x",), url=URL)


def test_a_remote_server_is_held_to_the_rules_of_the_lock() -> None:
    with pytest.raises(ValueError, match="takes no env variables"):
        remote(env=("TOKEN",))
    for bad in ("http://mcp.example.com/x", "https://user:pw@mcp.example.com/x", f"{URL}?key=1"):
        with pytest.raises(ValueError):
            remote(url=bad)
    with pytest.raises(ValueError, match="bearer variable that is not a name"):
        remote(bearer_env="lower")


def test_a_local_server_is_held_to_the_rules_of_the_lock() -> None:
    with pytest.raises(ValueError, match="bearer variable but no address"):
        local(bearer_env="TOKEN")
    for command in (("/usr/bin/npx", "server"), ("relative/server",), ["/bin/x"]):
        with pytest.raises(ValueError):
            local(command=command)
    with pytest.raises(ValueError, match="env name that is not capital"):
        local(env=("files_root",))
    for env in (("A", "A"), ["A"]):
        with pytest.raises(ValueError, match="each env variable once, in a tuple"):
            local(env=env)


def test_what_is_shown_to_a_person_is_what_would_be_typed() -> None:
    many = tuple(f"/opt/arg{n}" for n in range(64))
    assert len(local(command=("/opt/x", *many[:63])).command) == 64
    with pytest.raises(ValueError, match="more than 64 arguments"):
        local(command=("/opt/x", *many))
    assert len(local(command=("/opt/x", "a" * 1_000)).command[1]) == 1_000
    for bad in ("a" * 1_001, "a\x1bb", "a\nb"):
        with pytest.raises(ValueError, match="too long or not printable"):
            local(command=("/opt/x", bad))


# ----------------------------------------------------------------------------------- Plugin
def test_a_plugin_names_its_servers_and_skills_in_order() -> None:
    made = plugin(
        servers=(local(), remote(name="zed", bearer_env="")),
        skills=(skill("a_one"), skill("b_one")),
    )
    assert isinstance(made, PluginInterface) and made.identifier() == "research_pack@1"
    assert made.server_names() == ("files", "zed") and made.skill_names() == ("a_one", "b_one")


@pytest.mark.parametrize("name", ["", "Research", "1x", "a-b", 3])
def test_a_plugin_name_is_a_skill_name(name: Any) -> None:
    with pytest.raises(ValueError, match="plugin name"):
        plugin(name=name)


@pytest.mark.parametrize("version", [0, True, "1", 1.0])
def test_a_plugin_version_is_a_whole_number_from_one(version: Any) -> None:
    with pytest.raises(ValueError, match="whole number from 1"):
        plugin(version=version)


def test_a_description_is_one_short_line_of_printable_text() -> None:
    assert plugin(description="").description == ""
    assert len(plugin(description="x" * 300).description) == 300
    for bad in ("x" * 301, "two\nlines", "bell\x07", 5):
        with pytest.raises(ValueError, match="one line of printable text"):
            plugin(description=bad)


def test_a_plugin_is_made_of_tuples_and_bundles_something() -> None:
    for bad in ({"servers": [remote()]}, {"skills": [skill()]}):
        with pytest.raises(TypeError, match="tuples"):
            plugin(**bad)
    with pytest.raises(ValueError, match="at least one server or one skill"):
        plugin(servers=(), skills=())
    assert plugin(servers=(), skills=(skill(),)).server_names() == ()
    assert plugin(skills=()).skill_names() == ()


def test_a_plugin_bundles_a_bounded_number_of_servers_and_skills() -> None:
    servers = tuple(remote(name=f"s{n:02d}") for n in range(16))
    skills = tuple(skill(f"skill_{n:02d}") for n in range(16))
    assert len(plugin(servers=servers, skills=skills).servers) == 16
    with pytest.raises(ValueError, match="at most 16 servers and 16 skills"):
        plugin(servers=(*servers, remote(name="s16")), skills=skills)
    with pytest.raises(ValueError, match="at most 16 servers and 16 skills"):
        plugin(servers=servers, skills=(*skills, skill("skill_16")))


def test_each_server_and_skill_is_named_once_in_order() -> None:
    for bad in (
        {"servers": (local(), remote())},
        {"servers": (remote(), remote())},
        {"skills": (skill("b_one"), skill("a_one"))},
        {"skills": (skill("a_one"), skill("a_one"))},
    ):
        with pytest.raises(ValueError, match="once, in name order"):
            plugin(**bad)


# ------------------------------------------------------------------------- PluginLockEntry
def test_an_entry_records_the_bundle_hash_and_what_was_installed() -> None:
    made = entry()
    assert isinstance(made, PluginLockEntryInterface)
    assert made.identity() == f"research_pack@1:{A}"
    assert entry(servers=(), skills=()).skills == ()


@pytest.mark.parametrize("name", ["", "Pack", "a-b", 3])
def test_an_entry_name_is_a_plugin_name(name: Any) -> None:
    with pytest.raises(ValueError, match="locked plugin's name"):
        entry(name=name)


@pytest.mark.parametrize("version", [0, True, "1", 1.0])
def test_an_entry_version_is_a_whole_number_from_one(version: Any) -> None:
    with pytest.raises(ValueError, match="version that is not a whole number"):
        entry(version=version)


@pytest.mark.parametrize("digest", ["a" * 63, "A" * 64, "g" * 64, "", 5, None])
def test_an_entry_hash_is_64_lowercase_hex_digits(digest: Any) -> None:
    with pytest.raises(ValueError, match="64 lowercase hex"):
        entry(sha256=digest)


def test_an_entrys_servers_and_skills_are_tuples_of_the_right_shape() -> None:
    for bad in ({"servers": ["docs"]}, {"skills": [("a_one", A)]}):
        with pytest.raises(TypeError, match="tuples"):
            entry(**bad)
    for pair in (("a_one",), "ab", ("a", "b", "c")):
        with pytest.raises(TypeError, match="pair"):
            entry(skills=(pair,))
    for bad in (("Docs",), (3,)):
        with pytest.raises(ValueError, match="not a server name"):
            entry(servers=bad)
    for bad in ((("Bad", A),), ((3, A),)):
        with pytest.raises(ValueError, match="not a skill name"):
            entry(skills=bad)
    for bad in (("a_one", "short"), ("a_one", 5)):
        with pytest.raises(ValueError, match="skill hash that is not 64"):
            entry(skills=(bad,))


def test_an_entry_lists_servers_and_skills_once_each_in_order() -> None:
    for servers in (("files", "docs"), ("docs", "docs")):
        with pytest.raises(ValueError, match="servers once each, in order"):
            entry(servers=servers)
    for skills in ((("b_one", A), ("a_one", A)), (("a_one", A), ("a_one", B))):
        with pytest.raises(ValueError, match="skills once each, in order"):
            entry(skills=skills)


# ------------------------------------------------------------------------------- PluginLock
def test_a_plugin_lock_adds_finds_lists_and_removes() -> None:
    lock = PluginLock().with_entry(entry("zed_one")).with_entry(entry("alpha_one"))
    assert isinstance(lock, PluginLockInterface)
    assert lock.names() == ("alpha_one", "zed_one")
    found = lock.entry("zed_one")
    assert found is not None and found.name == "zed_one" and lock.entry("none") is None
    assert lock.without("zed_one").names() == ("alpha_one",)
    assert PluginLock.VERSION == 1


def test_a_plugin_that_is_installed_is_not_replaced_and_a_missing_one_is_not_removed() -> None:
    with pytest.raises(ValueError, match="'research_pack' is already installed"):
        PluginLock((entry(),)).with_entry(entry(sha256=B))
    with pytest.raises(ValueError, match="no plugin named 'none' is installed"):
        PluginLock().without("none")


def test_a_plugin_lock_is_a_tuple_of_entries_with_unique_names() -> None:
    with pytest.raises(TypeError, match="tuple"):
        PluginLock([entry()])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="share a name"):
        PluginLock((entry(), entry(sha256=B)))


def test_the_results_of_installing_and_removing_hold_what_changed() -> None:
    bundle = PluginBundle(plugin(), A)
    assert isinstance(bundle, PluginBundleInterface) and bundle.plugin.name == "research_pack"
    added = PluginAddition(PluginLock((entry(),)), SkillLock(), bundle)
    assert isinstance(added, PluginAdditionInterface) and added.bundle is bundle
    removed = PluginRemoval(PluginLock(), SkillLock(), ("a_one",), ("b_one",))
    assert isinstance(removed, PluginRemovalInterface)
    assert (removed.removed, removed.kept) == (("a_one",), ("b_one",))
