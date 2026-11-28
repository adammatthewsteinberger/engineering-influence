# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""A session selects MCP servers only by the name of a server the operator's lock already has."""

from pathlib import Path
from typing import Any

import pytest

from engineering_influence.infrastructure.in_memory_acp_session_store import InMemoryAcpSessionStore
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.interactions.acp.application import AcpApplication
from engineering_influence.models.mcp_server_lock import McpServerLock
from engineering_influence.models.tool_lock import ToolLock
from engineering_influence.services.brief_reader import BriefReader
from engineering_influence.services.cancel_run import CancelRun
from engineering_influence.services.create_run import CreateRun
from engineering_influence.services.resolve_spend_consent import ResolveSpendConsent
from engineering_influence.services.run_progress import RunProgress

INVALID = -32602


def server(name: str) -> McpServerLock:
    return McpServerLock(
        name=name,
        command=(f"/usr/local/bin/{name}-server",),
        files=((f"/usr/local/bin/{name}-server", "b" * 64),),
        env=(),
        server_name=name,
        server_version="1.0",
        tool_names=("search",),
        tools_hash="a" * 64,
    )


def lock_with(*names: str) -> ToolLock:
    return ToolLock(servers=tuple(server(name) for name in names))


def agent(store: InMemoryAcpSessionStore, locks: Any = None) -> AcpApplication:
    runs = InMemoryRunRepository()
    return AcpApplication(
        CreateRun(runs, InMemoryQueue()),
        CancelRun(runs),
        BriefReader(),
        RunProgress(runs),
        ResolveSpendConsent(runs, InMemoryQueue()),
        store,
        locks=locks,
    )


def new_session(app: AcpApplication, servers: list[Any]) -> dict[str, Any]:
    return app.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "session/new",
            "params": {"cwd": "/work/book", "mcpServers": servers},
        }
    )[0]


def test_a_session_with_no_servers_is_as_before() -> None:
    reply = new_session(agent(InMemoryAcpSessionStore()), [])
    assert "sessionId" in reply["result"]


def test_with_no_lock_a_session_cannot_select_any_server() -> None:
    reply = new_session(agent(InMemoryAcpSessionStore()), [{"name": "docs"}])
    assert reply["error"]["code"] == INVALID
    assert "not in the operator's lock" in reply["error"]["message"]


def test_a_locked_server_is_selected_and_stored_with_the_session() -> None:
    store = InMemoryAcpSessionStore()
    reply = new_session(agent(store, lambda cwd: lock_with("docs")), [{"name": "docs"}])
    session = store.get(reply["result"]["sessionId"])
    assert session is not None
    assert session.servers == ("docs",)


def test_a_command_or_url_in_place_of_a_locked_name_is_refused() -> None:
    locks = lambda cwd: lock_with("docs")
    for entry in ({"command": "curl"}, {"name": "rogue-server"}, {"name": 3}, "docs"):
        reply = new_session(agent(InMemoryAcpSessionStore(), locks), [entry])
        assert reply["error"]["code"] == INVALID, entry


def test_naming_a_server_twice_is_refused() -> None:
    reply = new_session(
        agent(InMemoryAcpSessionStore(), lambda cwd: lock_with("docs")),
        [{"name": "docs"}, {"name": "docs"}],
    )
    assert reply["error"]["code"] == INVALID
    assert "named twice" in reply["error"]["message"]


def test_mcp_servers_must_be_a_list() -> None:
    reply = new_session(
        agent(InMemoryAcpSessionStore(), lambda cwd: lock_with("docs")), {"name": "docs"}
    )  # type: ignore[arg-type]
    assert reply["error"]["code"] == INVALID


def test_the_lock_is_read_for_the_sessions_own_folder() -> None:
    seen: list[str] = []

    def locks(cwd: str) -> ToolLock:
        seen.append(cwd)
        return lock_with("docs")

    new_session(agent(InMemoryAcpSessionStore(), locks), [{"name": "docs"}])
    assert seen == ["/work/book"]


def test_a_reloaded_session_keeps_the_servers_it_selected() -> None:
    store = InMemoryAcpSessionStore()
    locks = lambda cwd: lock_with("docs")
    session_id = new_session(agent(store, locks), [{"name": "docs"}])["result"]["sessionId"]
    loaded = agent(store, locks).handle(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "session/load",
            "params": {"sessionId": session_id, "cwd": "/work/book"},
        }
    )
    assert "error" not in loaded[-1]
    stored = store.get(session_id)
    assert stored is not None and stored.servers == ("docs",)


def test_the_cli_reads_the_lock_named_by_the_environment_or_the_session_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from engineering_influence.infrastructure.tools.toml_tool_lock_store import TomlToolLockStore
    from engineering_influence.runtime.cli_runtime import CliRuntime

    folder = tmp_path / "book"
    folder.mkdir()
    TomlToolLockStore().save(folder / "ei-tools.lock.toml", lock_with("docs"))
    monkeypatch.delenv("EI_TOOL_LOCK", raising=False)
    assert CliRuntime._session_lock(str(folder)).server("docs") is not None
    elsewhere = tmp_path / "other.toml"
    TomlToolLockStore().save(elsewhere, lock_with("search"))
    monkeypatch.setenv("EI_TOOL_LOCK", str(elsewhere))
    assert CliRuntime._session_lock(str(folder)).server("search") is not None
    assert CliRuntime._session_lock(str(folder)).server("docs") is None
