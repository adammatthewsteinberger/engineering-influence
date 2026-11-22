# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The lock file carries grants, reads them strictly, and a lock without any is written as before."""

from pathlib import Path
from typing import Any

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.tools.toml_tool_lock_store import TomlToolLockStore
from engineering_influence.models.mcp_server_lock import McpServerLock
from engineering_influence.models.tool_lock import ToolLock

A, B = "a" * 64, "b" * 64


def server(**changes: Any) -> McpServerLock:
    fields: dict[str, Any] = {
        "name": "files",
        "command": ("/usr/bin/server",),
        "files": (("/usr/bin/server", A),),
        "env": (),
        "server_name": "s",
        "server_version": "1",
        "tool_names": ("list", "read", "write"),
        "tools_hash": B,
    }
    return McpServerLock(**{**fields, **changes})


def entry(grants: str = "") -> str:
    return (
        "version = 1\n[[server]]\n"
        'name = "files"\ncommand = ["/usr/bin/server"]\nserver_name = "s"\nserver_version = "1"\n'
        f'tool_names = ["list", "read", "write"]\ntools_hash = "{B}"\n'
        f'[server.files]\n"/usr/bin/server" = "{A}"\n{grants}'
    )


def load(tmp_path: Path, text: str) -> ToolLock | None:
    path = tmp_path / "lock.toml"
    path.write_text(text, encoding="utf-8")
    return TomlToolLockStore().load(path)


def refused(tmp_path: Path, text: str) -> str:
    with pytest.raises(ApplicationError) as error:
        load(tmp_path, text)
    assert (error.value.code, error.value.http_status) == ("TOOL_LOCK_INVALID", 422)
    return error.value.message


def test_grants_survive_a_save_and_a_load(tmp_path: Path) -> None:
    lock = ToolLock((server(grants=(("outline", ("read",)), ("research", ("list", "read")))),))
    path = tmp_path / "lock.toml"
    TomlToolLockStore().save(path, lock)
    assert TomlToolLockStore().load(path) == lock


def test_the_grants_are_written_as_their_own_table_after_the_files() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "lock.toml"
        TomlToolLockStore().save(
            path, ToolLock((server(grants=(("research", ("list", "read")),)),))
        )
        text = path.read_text(encoding="utf-8")
    assert text.endswith(
        f'[server.files]\n"/usr/bin/server" = "{A}"\n\n[server.grants]\nresearch = ["list", "read"]\n'
    )


def test_a_lock_with_no_grants_has_no_grants_table_so_existing_files_are_unchanged() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "lock.toml"
        TomlToolLockStore().save(path, ToolLock((server(),)))
        assert "grants" not in path.read_text(encoding="utf-8")


def test_a_file_with_no_grants_loads_with_none(tmp_path: Path) -> None:
    lock = load(tmp_path, entry())
    assert lock is not None and lock.servers[0].grants == ()


def test_a_hand_edited_grant_in_any_order_loads_sorted(tmp_path: Path) -> None:
    lock = load(
        tmp_path, entry('[server.grants]\nresearch = ["write", "list"]\noutline = ["read"]\n')
    )
    assert lock is not None
    assert lock.servers[0].grants == (("outline", ("read",)), ("research", ("list", "write")))


def test_grants_that_are_not_a_table_are_refused(tmp_path: Path) -> None:
    text = entry().replace("[server.files]", 'grants = ["research"]\n[server.files]')
    message = refused(tmp_path, text)
    assert "server #1 (files)" in message and "table of stage" in message


def test_a_stages_tools_that_are_text_and_not_a_list_are_refused(tmp_path: Path) -> None:
    assert "expected a list" in refused(tmp_path, entry('[server.grants]\nresearch = "read"\n'))


def test_a_grant_of_a_tool_the_lock_does_not_list_is_refused_naming_the_entry(
    tmp_path: Path,
) -> None:
    message = refused(tmp_path, entry('[server.grants]\nresearch = ["delete"]\n'))
    assert (
        "server #1 (files)" in message
        and "'delete' is not one of the tools this lock lists" in message
    )


def test_a_stage_with_an_empty_grant_is_refused(tmp_path: Path) -> None:
    assert "non-empty" in refused(tmp_path, entry("[server.grants]\nresearch = []\n"))


def test_a_grant_for_a_stage_with_a_bad_name_is_refused(tmp_path: Path) -> None:
    assert "names a stage" in refused(tmp_path, entry('[server.grants]\n"Bad Stage" = ["read"]\n'))
