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


def agent(
    store: InMemoryAcpSessionStore, locks: Any = None, runs: InMemoryRunRepository | None = None
) -> AcpApplication:
    runs = InMemoryRunRepository() if runs is None else runs
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


BRIEF = 'kind = "nonfiction"\nidea = "Windowsill herbs"\nbudget_micro_usd = 5000000\n'


def answer(app: AcpApplication, request: dict[str, Any], option: str) -> list[dict[str, Any]]:
    """The client's answer to a permission request, as a response with the request's id."""
    return app.handle(
        {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {"outcome": {"outcome": "selected", "optionId": option}},
        }
    )


def prompt(app: AcpApplication, session_id: str, text: str = BRIEF) -> list[dict[str, Any]]:
    return app.handle(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "session/prompt",
            "params": {"sessionId": session_id, "prompt": [{"type": "text", "text": text}]},
        }
    )


def answer_all(
    app: AcpApplication, messages: list[dict[str, Any]], option: str = "allow"
) -> list[dict[str, Any]]:
    """Answer every approval the messages ask for, in order, and return what the answers produced."""
    produced: list[dict[str, Any]] = []
    queue = list(messages)
    while queue:
        message = queue.pop(0)
        if message.get("method") == "session/request_permission":
            produced_now = answer(app, message, option)
            queue.extend(produced_now)
            produced.extend(produced_now)
        else:
            produced.append(message)
    return produced


def started_run(runs: InMemoryRunRepository, servers: list[Any], locks: Any) -> Any:
    store = InMemoryAcpSessionStore()
    app = agent(store, locks, runs)
    session_id = new_session(app, servers)["result"]["sessionId"]
    answer_all(app, prompt(app, session_id))
    run_id = store.get(session_id).run_id
    assert run_id is not None
    return runs.get(run_id)


def test_a_prompt_starts_a_run_that_may_use_only_the_servers_its_session_selected() -> None:
    run = started_run(
        InMemoryRunRepository(), [{"name": "docs"}], lambda cwd: lock_with("docs", "maps")
    )
    assert run is not None and run.servers == ("docs",)


def test_a_session_that_selected_no_servers_starts_a_run_that_may_use_none() -> None:
    run = started_run(InMemoryRunRepository(), [], lambda cwd: lock_with("docs"))
    assert run is not None and run.servers == ()


def test_a_prompt_asks_before_a_selected_server_starts_and_names_it_and_its_tools() -> None:
    store = InMemoryAcpSessionStore()
    app = agent(store, lambda cwd: lock_with("docs"))
    session_id = new_session(app, [{"name": "docs"}])["result"]["sessionId"]
    messages = prompt(app, session_id)
    assert [m["method"] for m in messages] == ["session/request_permission"]
    request = messages[0]
    assert (
        "'docs'" in request["params"]["toolCall"]["title"]
        and "search" in request["params"]["toolCall"]["title"]
    )
    assert store.get(session_id).run_id is None  # nothing has started


def test_an_approved_server_starts_the_run_and_the_approval_is_kept_with_the_session() -> None:
    runs = InMemoryRunRepository()
    store = InMemoryAcpSessionStore()
    app = agent(store, lambda cwd: lock_with("docs"), runs)
    session_id = new_session(app, [{"name": "docs"}])["result"]["sessionId"]
    replies = answer_all(app, prompt(app, session_id))
    assert replies[-1]["result"] == {"stopReason": "end_turn"}
    assert store.get(session_id).approved == ("docs",)


def test_every_selected_server_is_asked_for_in_turn_and_all_of_them_start_the_run() -> None:
    runs = InMemoryRunRepository()
    store = InMemoryAcpSessionStore()
    app = agent(store, lambda cwd: lock_with("docs", "maps"), runs)
    session_id = new_session(app, [{"name": "maps"}, {"name": "docs"}])["result"]["sessionId"]
    first = prompt(app, session_id)
    assert (
        "'maps'" in first[0]["params"]["toolCall"]["title"]
    )  # asked in the order the session selected them
    second = answer(app, first[0], "allow")
    assert "'docs'" in second[0]["params"]["toolCall"]["title"]
    answer(app, second[0], "allow")
    run_id = store.get(session_id).run_id
    assert run_id is not None and runs.get(run_id).servers == ("maps", "docs")


def test_a_refused_server_starts_no_run_and_the_prompt_ends_as_a_refusal() -> None:
    runs = InMemoryRunRepository()
    store = InMemoryAcpSessionStore()
    app = agent(store, lambda cwd: lock_with("docs"), runs)
    session_id = new_session(app, [{"name": "docs"}])["result"]["sessionId"]
    replies = answer_all(app, prompt(app, session_id), option="deny")
    assert replies[-1]["result"] == {"stopReason": "refusal"}
    assert store.get(session_id).run_id is None and store.get(session_id).approved == ()


def test_a_cancelled_approval_ends_the_prompt_as_cancelled_and_starts_nothing() -> None:
    store = InMemoryAcpSessionStore()
    app = agent(store, lambda cwd: lock_with("docs"))
    session_id = new_session(app, [{"name": "docs"}])["result"]["sessionId"]
    request = prompt(app, session_id)[0]
    replies = app.handle(
        {"jsonrpc": "2.0", "id": request["id"], "result": {"outcome": {"outcome": "cancelled"}}}
    )
    assert replies[-1]["result"] == {"stopReason": "cancelled"}
    assert store.get(session_id).run_id is None


def test_an_answer_the_request_does_not_understand_keeps_the_prompt_waiting() -> None:
    store = InMemoryAcpSessionStore()
    app = agent(store, lambda cwd: lock_with("docs"))
    session_id = new_session(app, [{"name": "docs"}])["result"]["sessionId"]
    request = prompt(app, session_id)[0]
    assert (
        app.handle(
            {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {"outcome": {"outcome": "selected", "optionId": "maybe"}},
            }
        )
        == []
    )
    assert store.get(session_id).run_id is None


def test_an_approval_survives_a_reload_so_the_server_is_not_asked_for_again() -> None:
    store = InMemoryAcpSessionStore()
    app = agent(store, lambda cwd: lock_with("docs"))
    session_id = new_session(app, [{"name": "docs"}])["result"]["sessionId"]
    answer_all(app, prompt(app, session_id))
    kept = store.get(session_id)
    assert kept.approved == ("docs",) and kept.run_id is not None


def test_a_server_the_operator_removed_from_the_lock_before_approval_is_refused() -> None:
    current = {"lock": lock_with("docs")}
    store = InMemoryAcpSessionStore()
    app = agent(store, lambda cwd: current["lock"])
    session_id = new_session(app, [{"name": "docs"}])["result"]["sessionId"]
    current["lock"] = lock_with()  # the operator takes it out of the lock
    reply = prompt(app, session_id)[0]
    assert reply["error"]["code"] == INVALID
    assert "not in the operator's lock" in reply["error"]["message"]
    assert store.get(session_id).run_id is None
