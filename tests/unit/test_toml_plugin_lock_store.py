# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""TomlPluginLockStore: a record that reads strictly, writes the same bytes every time, and is never half written."""

from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.plugins.toml_plugin_lock_store import (
    TomlPluginLockStore,
)
from engineering_influence.interfaces.plugin_lock_store_interface import PluginLockStoreInterface
from engineering_influence.models.plugin_lock import PluginLock
from engineering_influence.models.plugin_lock_entry import PluginLockEntry

A, B = "a" * 64, "b" * 64


def entry(
    name: str, sha: str = A, servers: tuple[str, ...] = (), skills: tuple[tuple[str, str], ...] = ()
) -> PluginLockEntry:
    return PluginLockEntry(name, 3, sha, servers, skills)


def store() -> TomlPluginLockStore:
    return TomlPluginLockStore()


def loading(tmp_path: Path, text: str) -> ApplicationError:
    path = tmp_path / "lock.toml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ApplicationError) as error:
        store().load(path)
    assert error.value.code == "PLUGIN_LOCK_INVALID" and error.value.http_status == 422
    return error.value


def block(**changes: str) -> str:
    fields = {
        "name": '"pack"',
        "version": "3",
        "sha256": f'"{A}"',
        "servers": '["docs"]',
        "skills": None,
    }
    given = {**fields, **changes}
    skills = given.pop("skills")
    text = "[[plugin]]\n" + "".join(f"{k} = {v}\n" for k, v in given.items())
    return text + (
        f"skills = {skills}\n" if skills is not None else f'[plugin.skills]\nplain = "{B}"\n'
    )


def test_it_is_a_plugin_lock_store() -> None:
    assert isinstance(store(), PluginLockStoreInterface)


def test_a_missing_file_is_no_lock() -> None:
    assert store().load(Path("/nonexistent/ei-plugins.lock.toml")) is None


def test_a_lock_survives_a_save_and_a_load(tmp_path: Path) -> None:
    path = tmp_path / "lock.toml"
    lock = PluginLock(
        (entry("zed", B, ("docs", "files"), (("a_one", A), ("b_one", B))), entry("alpha"))
    )
    store().save(path, lock)
    loaded = store().load(path)
    assert loaded is not None and set(loaded.entries) == set(lock.entries)


def test_the_layout_is_fixed_with_plugins_in_name_order(tmp_path: Path) -> None:
    path = tmp_path / "lock.toml"
    store().save(
        path, PluginLock((entry("zed", servers=("docs",), skills=(("a_one", B),)), entry("alpha")))
    )
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# Installed plugins: reviewed bundles")
    assert "A run never reads it" in text
    assert text.index('name = "alpha"') < text.index('name = "zed"')
    assert text.count("[[plugin]]") == 2 and text.count("version = 1\n") == 1
    assert f'sha256 = "{A}"\nservers = ["docs"]\n\n[plugin.skills]\na_one = "{B}"\n' in text
    assert "servers = []\n\n[plugin.skills]\n" in text


def test_two_saves_give_the_same_bytes_and_leave_no_temporary_file(tmp_path: Path) -> None:
    path = tmp_path / "lock.toml"
    store().save(path, PluginLock((entry("b"), entry("a"))))
    first = path.read_bytes()
    store().save(path, PluginLock((entry("a"), entry("b"))))
    assert path.read_bytes() == first
    assert sorted(item.name for item in tmp_path.iterdir()) == ["lock.toml"]


def test_a_stale_temporary_link_is_never_written_through(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere.txt"
    elsewhere.write_text("untouched", encoding="utf-8")
    (tmp_path / ".lock.toml.tmp").symlink_to(elsewhere)
    store().save(tmp_path / "lock.toml", PluginLock((entry("a"),)))
    assert elsewhere.read_text(encoding="utf-8") == "untouched"
    loaded = store().load(tmp_path / "lock.toml")
    assert loaded is not None and loaded.names() == ("a",)


def test_an_empty_lock_is_a_valid_file(tmp_path: Path) -> None:
    path = tmp_path / "lock.toml"
    store().save(path, PluginLock())
    loaded = store().load(path)
    assert loaded is not None and loaded.entries == ()


def test_a_file_that_cannot_be_read_is_an_error_that_names_it(tmp_path: Path) -> None:
    (tmp_path / "folder").mkdir()
    with pytest.raises(ApplicationError, match=r"cannot read .*folder.*IsADirectoryError"):
        store().load(tmp_path / "folder")
    (tmp_path / "binary.toml").write_bytes(b"\xff\xfe")
    with pytest.raises(ApplicationError, match="UnicodeDecodeError"):
        store().load(tmp_path / "binary.toml")


def test_text_that_is_not_toml_or_has_an_unknown_top_level_key_is_refused(tmp_path: Path) -> None:
    assert "is not valid TOML" in loading(tmp_path, "version = ").message
    assert "unknown top-level key 'extra'" in loading(tmp_path, "version = 1\nextra = 1\n").message


@pytest.mark.parametrize("version", ["", "version = 2\n", 'version = "1"\n', "version = true\n"])
def test_a_version_this_does_not_read_is_refused(tmp_path: Path, version: str) -> None:
    assert "this reads 1" in loading(tmp_path, version).message


def test_plugin_entries_must_be_a_list_of_tables(tmp_path: Path) -> None:
    assert (
        "not a list of tables" in loading(tmp_path, "version = 1\n[plugin]\nname = 'x'\n").message
    )
    assert (
        "plugin #1 (?) is not a table" in loading(tmp_path, "version = 1\nplugin = [1]\n").message
    )


def test_an_entry_with_an_unknown_or_missing_key_is_refused_and_named(tmp_path: Path) -> None:
    message = loading(tmp_path, "version = 1\n" + block(extra="1")).message
    assert "plugin #1 (pack) has an unknown key 'extra'" in message
    text = "version = 1\n[[plugin]]\nname = 'pack'\nversion = 3\nsha256 = 'x'\nservers = []\n"
    assert "plugin #1 (pack) is missing 'skills'" in loading(tmp_path, text).message
    assert (
        "plugin #1 (?) is missing 'name'"
        in loading(
            tmp_path,
            "version = 1\n[[plugin]]\nversion = 3\nsha256 = 'x'\nservers = []\n[plugin.skills]\n",
        ).message
    )


def test_servers_must_be_a_list_and_skills_a_table(tmp_path: Path) -> None:
    text = "version = 1\n" + block(servers='"docs"')
    assert "has servers that are not a list" in loading(tmp_path, text).message
    text = "version = 1\n" + block(skills='["a"]')
    assert "skills that are not a table of name = hash" in loading(tmp_path, text).message


def test_what_the_model_refuses_is_an_error_that_names_the_entry(tmp_path: Path) -> None:
    for changes, expected in (
        ({"sha256": '"abc"'}, "64 lowercase hex"),
        ({"version": '"3"'}, "version that is not a whole number"),
        ({"name": '"Pack"'}, "locked plugin's name"),
        ({"servers": '["Docs"]'}, "not a server name"),
        ({"servers": '["files", "docs"]'}, "servers once each"),
    ):
        message = loading(tmp_path, "version = 1\n" + block(**changes)).message
        assert expected in message and message.startswith("plugin #1 (")


def test_a_lock_the_model_refuses_as_a_whole_is_an_error(tmp_path: Path) -> None:
    assert "share a name" in loading(tmp_path, "version = 1\n" + block() + block()).message


def test_a_text_with_odd_characters_is_written_safely() -> None:
    assert TomlPluginLockStore._quote('a"b\\c\n\x7f') == '"a\\"b\\\\c\\u000a\\u007f"'
