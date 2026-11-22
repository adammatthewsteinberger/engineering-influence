# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""TomlToolLockStore: a lock that reads strictly, writes the same bytes every time, and is never half written."""

from pathlib import Path
from typing import Any

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.tools.toml_tool_lock_store import TomlToolLockStore
from engineering_influence.interfaces.tool_lock_store_interface import ToolLockStoreInterface
from engineering_influence.models.mcp_server_lock import McpServerLock
from engineering_influence.models.tool_lock import ToolLock

A, B = "a" * 64, "b" * 64


def server(name: str = "files", **changes: Any) -> McpServerLock:
    fields: dict[str, Any] = {
        "name": name,
        "command": ("/usr/bin/server", "/opt/server.js", "--flag"),
        "files": (("/opt/server.js", B), ("/usr/bin/server", A)),
        "env": ("FILES_ROOT", "TOKEN"),
        "server_name": "files-server",
        "server_version": "1.2.0",
        "tool_names": ("read", "write"),
        "tools_hash": A,
    }
    return McpServerLock(**{**fields, **changes})


def store() -> TomlToolLockStore:
    return TomlToolLockStore()


def test_it_is_a_tool_lock_store() -> None:
    assert isinstance(store(), ToolLockStoreInterface)


def test_a_missing_file_is_no_lock() -> None:
    assert store().load(Path("/nonexistent/ei-tools.lock.toml")) is None


def test_a_lock_survives_a_save_and_a_load(tmp_path: Path) -> None:
    path = tmp_path / "ei-tools.lock.toml"
    lock = ToolLock((server("zed"), server("alpha", env=(), tool_names=())))
    store().save(path, lock)
    loaded = store().load(path)
    assert loaded is not None
    assert set(loaded.servers) == set(lock.servers)


def test_the_file_is_written_in_a_fixed_layout_with_servers_in_name_order(tmp_path: Path) -> None:
    path = tmp_path / "lock.toml"
    store().save(path, ToolLock((server("zed", env=()), server("alpha"))))
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# Locked MCP tool servers.")
    assert text.index('name = "alpha"') < text.index('name = "zed"')
    assert text.count("[[server]]") == 2 and text.count("version = 1") == 1
    expected = (
        "[[server]]\n"
        'name = "alpha"\n'
        'command = ["/usr/bin/server", "/opt/server.js", "--flag"]\n'
        'env = ["FILES_ROOT", "TOKEN"]\n'
        'server_name = "files-server"\n'
        'server_version = "1.2.0"\n'
        'tool_names = ["read", "write"]\n'
        f'tools_hash = "{A}"\n'
        "\n"
        "[server.files]\n"
        f'"/opt/server.js" = "{B}"\n'
        f'"/usr/bin/server" = "{A}"\n'
    )
    assert expected in text


def test_saving_the_same_lock_twice_gives_the_same_bytes(tmp_path: Path) -> None:
    lock = ToolLock((server("b"), server("a")))
    one, two = tmp_path / "one.toml", tmp_path / "two.toml"
    store().save(one, lock)
    store().save(two, ToolLock(tuple(reversed(lock.servers))))
    assert one.read_bytes() == two.read_bytes()


def test_an_empty_lock_is_just_the_header_and_version(tmp_path: Path) -> None:
    path = tmp_path / "lock.toml"
    store().save(path, ToolLock())
    loaded = store().load(path)
    assert loaded == ToolLock()
    assert "[[server]]" not in path.read_text(encoding="utf-8")


def test_special_characters_in_text_round_trip(tmp_path: Path) -> None:
    odd = 'quote " back \\ tab \t newline \n del \x7f bell \x07 café 😀 \u2028'
    lock = ToolLock((server(server_name=odd, server_version="1\\2", tool_names=(odd, "plain")),))
    path = tmp_path / "lock.toml"
    store().save(path, lock)
    loaded = store().load(path)
    assert loaded == lock


def test_saving_replaces_the_old_file_and_leaves_no_temporary_one(tmp_path: Path) -> None:
    path = tmp_path / "lock.toml"
    path.write_text("old contents", encoding="utf-8")
    store().save(path, ToolLock((server(),)))
    assert "old contents" not in path.read_text(encoding="utf-8")
    assert sorted(entry.name for entry in tmp_path.iterdir()) == ["lock.toml"]


# ------------------------------------------------------------------------------- loading
def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "lock.toml"
    path.write_text(text, encoding="utf-8")
    return path


def good_entry(extra: str = "", drop: str = "") -> str:
    lines = [
        "[[server]]",
        'name = "files"',
        'command = ["/usr/bin/server"]',
        'server_name = "s"',
        'server_version = "1"',
        f'tools_hash = "{A}"',
        extra,
        "[server.files]",
        f'"/usr/bin/server" = "{A}"',
    ]
    return "\n".join(line for line in lines if line and (not drop or not line.startswith(drop)))


def refused(path: Path) -> str:
    with pytest.raises(ApplicationError) as error:
        store().load(path)
    assert (error.value.code, error.value.http_status) == ("TOOL_LOCK_INVALID", 422)
    return error.value.message


def test_the_minimal_entry_loads_with_no_env_and_no_tool_names(tmp_path: Path) -> None:
    lock = store().load(write(tmp_path, "version = 1\n" + good_entry()))
    assert lock is not None and lock.servers[0].env == () and lock.servers[0].tool_names == ()


def test_a_file_that_is_not_toml_is_refused_with_its_path(tmp_path: Path) -> None:
    path = write(tmp_path, "version = = 1")
    message = refused(path)
    assert str(path) in message and "not valid TOML" in message


def test_a_file_that_cannot_be_read_is_refused(tmp_path: Path) -> None:
    assert "cannot read" in refused(tmp_path)  # a directory


def test_a_file_that_is_not_utf8_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "lock.toml"
    path.write_bytes(b"version = 1\n# \xff\xfe\n")
    assert "cannot read" in refused(path)


def test_an_unknown_top_level_key_is_refused(tmp_path: Path) -> None:
    assert "unknown top-level key 'extra'" in refused(write(tmp_path, "version = 1\nextra = 2\n"))


@pytest.mark.parametrize(
    "text",
    [
        "",
        "[[server]]\nname = 'x'\n",
        "version = 2\n",
        'version = "1"\n',
        "version = true\n",
        "version = 1.0\n",
    ],
)
def test_a_missing_or_other_version_is_refused(tmp_path: Path, text: str) -> None:
    assert "this reads 1" in refused(write(tmp_path, text))


def test_a_server_that_is_not_a_table_is_refused(tmp_path: Path) -> None:
    assert "is not a table" in refused(write(tmp_path, 'version = 1\nserver = ["x"]\n'))


def test_an_unknown_key_in_an_entry_is_refused_and_names_the_entry(tmp_path: Path) -> None:
    message = refused(write(tmp_path, "version = 1\n" + good_entry('extra = "x"')))
    assert "server #1 (files)" in message and "unknown key 'extra'" in message


@pytest.mark.parametrize("key", ["name", "command", "server_name", "server_version", "tools_hash"])
def test_a_missing_required_key_is_refused(tmp_path: Path, key: str) -> None:
    message = refused(write(tmp_path, "version = 1\n" + good_entry(drop=key)))
    assert f"is missing {key!r}" in message


def test_a_missing_files_table_is_refused(tmp_path: Path) -> None:
    text = good_entry().split("[server.files]")[0]
    assert "is missing 'files'" in refused(write(tmp_path, "version = 1\n" + text))


def test_files_that_are_not_a_table_are_refused(tmp_path: Path) -> None:
    text = good_entry().split("[server.files]")[0] + 'files = ["x"]\n'
    assert "files that are not a table" in refused(write(tmp_path, "version = 1\n" + text))


def test_a_command_that_is_text_and_not_a_list_is_refused(tmp_path: Path) -> None:
    text = good_entry().replace('command = ["/usr/bin/server"]', 'command = "/usr/bin/server"')
    assert "expected a list" in refused(write(tmp_path, "version = 1\n" + text))


@pytest.mark.parametrize("line", ['env = "X"', 'tool_names = "x"'])
def test_an_optional_list_that_is_text_is_refused(tmp_path: Path, line: str) -> None:
    assert "expected a list" in refused(write(tmp_path, "version = 1\n" + good_entry(line)))


def test_an_entry_the_model_refuses_is_reported_with_the_entry_and_the_reason(
    tmp_path: Path,
) -> None:
    text = good_entry().replace('command = ["/usr/bin/server"]', 'command = ["server"]')
    message = refused(write(tmp_path, "version = 1\n" + text))
    assert "server #1 (files)" in message and "absolute path" in message


def test_a_launcher_in_the_file_is_refused_on_load(tmp_path: Path) -> None:
    text = good_entry().replace("/usr/bin/server", "/usr/bin/npx")
    assert "npx fetches code" in refused(write(tmp_path, "version = 1\n" + text))


def test_two_servers_with_the_same_name_are_refused(tmp_path: Path) -> None:
    assert "share a name" in refused(
        write(tmp_path, "version = 1\n" + good_entry() + "\n" + good_entry())
    )


def test_a_hash_that_is_not_text_is_refused(tmp_path: Path) -> None:
    text = good_entry().replace(f'tools_hash = "{A}"', "tools_hash = 5")
    assert "server #1 (files)" in refused(write(tmp_path, "version = 1\n" + text))


def test_a_hand_edited_files_table_in_any_order_still_loads(tmp_path: Path) -> None:
    reversed_files = good_entry().replace(
        f'"/usr/bin/server" = "{A}"', f'"/zzz/script.js" = "{B}"\n"/usr/bin/server" = "{A}"'
    )
    lock = store().load(write(tmp_path, "version = 1\n" + reversed_files))
    assert lock is not None
    assert [path for path, _ in lock.servers[0].files] == ["/usr/bin/server", "/zzz/script.js"]


# ------------------------------------------------------------------------------ a remote server
def remote(name: str = "docs", **changes: Any) -> McpServerLock:
    fields: dict[str, Any] = {
        "name": name,
        "command": (),
        "files": (),
        "env": (),
        "server_name": "docs-server",
        "server_version": "2.0.0",
        "tool_names": ("read", "search"),
        "tools_hash": B,
        "url": "https://mcp.example.com/mcp",
        "bearer_env": "DOCS_TOKEN",
    }
    return McpServerLock(**{**fields, **changes})


def test_a_remote_entry_is_written_as_an_address_with_no_command_or_files(tmp_path: Path) -> None:
    path = tmp_path / "lock.toml"
    store().save(path, ToolLock((remote(grants=(("research", ("search",)),)),)))
    text = path.read_text(encoding="utf-8")
    assert 'url = "https://mcp.example.com/mcp"\nbearer_env = "DOCS_TOKEN"\n' in text
    assert "\ncommand = " not in text and "[server.files]" not in text and "\nenv = " not in text
    assert '[server.grants]\nresearch = ["search"]\n' in text


def test_a_remote_entry_without_a_bearer_variable_writes_no_bearer_line(tmp_path: Path) -> None:
    path = tmp_path / "lock.toml"
    store().save(path, ToolLock((remote(bearer_env=""),)))
    assert "bearer_env" not in path.read_text(encoding="utf-8")


def test_local_and_remote_entries_survive_a_save_and_a_load_together(tmp_path: Path) -> None:
    path = tmp_path / "lock.toml"
    lock = ToolLock(
        (
            remote("zed"),
            server("alpha"),
            remote("mid", bearer_env="", grants=(("research", ("read", "search")),)),
        )
    )
    store().save(path, lock)
    loaded = store().load(path)
    assert loaded is not None and set(loaded.servers) == set(lock.servers)
    store().save(tmp_path / "again.toml", loaded)
    assert (tmp_path / "again.toml").read_bytes() == path.read_bytes()


def test_a_local_entry_is_written_exactly_as_before(tmp_path: Path) -> None:
    path = tmp_path / "lock.toml"
    store().save(path, ToolLock((server(),)))
    assert path.read_text(encoding="utf-8").split("[[server]]\n")[1] == (
        'name = "files"\n'
        'command = ["/usr/bin/server", "/opt/server.js", "--flag"]\n'
        'env = ["FILES_ROOT", "TOKEN"]\n'
        'server_name = "files-server"\n'
        'server_version = "1.2.0"\n'
        'tool_names = ["read", "write"]\n'
        f'tools_hash = "{A}"\n'
        "\n"
        "[server.files]\n"
        f'"/opt/server.js" = "{B}"\n'
        f'"/usr/bin/server" = "{A}"\n'
    )


def remote_entry(extra: str = "", drop: str = "") -> str:
    lines = [
        "[[server]]",
        'name = "docs"',
        'url = "https://mcp.example.com/mcp"',
        'server_name = "s"',
        'server_version = "1"',
        f'tools_hash = "{A}"',
        extra,
    ]
    return "\n".join(line for line in lines if line and (not drop or not line.startswith(drop)))


def test_a_hand_written_remote_entry_loads(tmp_path: Path) -> None:
    loaded = store().load(
        write(tmp_path, "version = 1\n" + remote_entry('bearer_env = "DOCS_TOKEN"'))
    )
    assert loaded is not None
    [found] = loaded.servers
    assert found.remote() and found.url == "https://mcp.example.com/mcp"
    assert found.bearer_env == "DOCS_TOKEN" and found.files == () and found.command == ()


@pytest.mark.parametrize("extra", ['command = ["/usr/bin/server"]', "env = []", "[server.files]"])
def test_a_remote_entry_with_a_command_files_or_env_is_refused(tmp_path: Path, extra: str) -> None:
    message = refused(write(tmp_path, "version = 1\n" + remote_entry(extra)))
    assert "has an address, so it cannot have a command, files or env variables" in message


@pytest.mark.parametrize("key", ["name", "server_name", "server_version", "tools_hash"])
def test_a_remote_entry_missing_a_required_key_is_refused(tmp_path: Path, key: str) -> None:
    assert f"is missing {key!r}" in refused(
        write(tmp_path, "version = 1\n" + remote_entry(drop=key))
    )


def test_a_remote_entry_with_an_address_the_model_refuses_is_refused_with_the_reason(
    tmp_path: Path,
) -> None:
    text = remote_entry().replace("https://mcp.example.com/mcp", "http://mcp.example.com/mcp")
    message = refused(write(tmp_path, "version = 1\n" + text))
    assert "server #1 (docs)" in message and "never plain http" in message


def test_an_address_that_is_not_text_is_refused(tmp_path: Path) -> None:
    text = remote_entry().replace('url = "https://mcp.example.com/mcp"', "url = 5")
    assert "server #1 (docs)" in refused(write(tmp_path, "version = 1\n" + text))


def test_a_local_entry_with_a_bearer_variable_is_refused(tmp_path: Path) -> None:
    message = refused(write(tmp_path, "version = 1\n" + good_entry('bearer_env = "TOKEN"')))
    assert "only a remote server has a bearer variable" in message
