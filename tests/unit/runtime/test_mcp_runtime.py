"""The MCP server wired to the stack's database and queue, and what a host sees when it starts it."""

import json
import logging
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.observability.process_crash_hooks import ProcessCrashHooks
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.repositories.sqlmodel_artifact_store import SqlModelArtifactStore
from engineering_influence.repositories.sqlmodel_run_repository import SqlModelRunRepository
from engineering_influence.runtime.app_settings import AppSettings
from engineering_influence.runtime.interfaces.mcp_runtime_interface import McpRuntimeInterface
from engineering_influence.runtime.mcp_runtime import McpRuntime
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes

BROKER = "amqp://svc:rabbitpw@127.0.0.1:1/"
READ = {
    "start_pipeline",
    "create_run",
    "list_runs",
    "resume_run",
    "cancel_run",
    "get_run",
    "read_artifact",
}
SPEND = {"grant_run", "deny_run"}


@pytest.fixture
def process_state() -> Iterator[None]:
    """Running a server configures logging and installs crash hooks; put the process back as it was."""
    root = logging.getLogger()
    saved_handlers, saved_level = list(root.handlers), root.level
    saved_hook, saved_flag = sys.excepthook, ProcessCrashHooks._installed
    ProcessCrashHooks._installed = False
    yield
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)
    sys.excepthook = saved_hook
    ProcessCrashHooks._installed = saved_flag


def tools_of(server: Any) -> dict[str, Any]:
    return {name: tool.fn for name, tool in server._tool_manager._tools.items()}


def seed(database_url: str) -> None:
    brief = BookBrief(BookKind.NONFICTION, "Windowsill herbs", 5_000_000)
    runs = SqlModelRunRepository(database_url)
    runs.save(BookRun("run-1", brief, NonfictionRecipes().plan(), Budget(cap=5_000_000)).start())
    runs.close()
    artifacts = SqlModelArtifactStore(database_url)
    artifacts.put("run-1", "book/herbs.pdf", b"%PDF-1.7\xff")
    artifacts.put("run-1", "brief.md", b"A brief.")
    artifacts.close()


def runtime(database_url: str, **changes: Any) -> McpRuntime:
    return McpRuntime(AppSettings(database_url, BROKER, **changes), queue=InMemoryQueue())


def test_it_is_an_mcp_runtime(database_url: str) -> None:
    assert isinstance(runtime(database_url), McpRuntimeInterface)


def test_the_server_offers_runs_and_their_files_but_not_the_persons_money(
    database_url: str,
) -> None:
    mcp = runtime(database_url)
    try:
        assert set(tools_of(mcp.build_server())) == READ
    finally:
        mcp.close()


def test_the_operator_can_let_the_server_grant_and_deny_budget(database_url: str) -> None:
    mcp = runtime(database_url, mcp_allow_spend=True)
    try:
        assert set(tools_of(mcp.build_server())) == READ | SPEND
    finally:
        mcp.close()


def test_the_tools_work_on_the_stacks_own_database(database_url: str) -> None:
    seed(database_url)
    queue = InMemoryQueue()
    mcp = McpRuntime(AppSettings(database_url, BROKER), queue=queue)
    try:
        tools = tools_of(mcp.build_server())
        assert [run["run_id"] for run in tools["list_runs"]()] == ["run-1"]
        assert tools["get_run"]("run-1")["artifacts"] == ["book/herbs.pdf", "brief.md"]
        assert tools["read_artifact"]("run-1", "brief.md")["content"] == "A brief."
        assert tools["read_artifact"]("run-1", "book/herbs.pdf")["encoding"] == "base64"
        started = tools["create_run"](
            {"schema_version": 1, "kind": "novel", "idea": "A road", "budget_micro_usd": 1_000_000}
        )
        assert started["status"] == "pending" and len(queue.jobs) == 1
        assert tools["cancel_run"]("run-1")["status"] == "cancelled"
    finally:
        mcp.close()


def test_a_database_that_was_never_migrated_is_refused_with_the_way_to_fix_it(
    tmp_path: Path,
) -> None:
    mcp = McpRuntime(
        AppSettings(f"sqlite:///{tmp_path / 'fresh.db'}", BROKER), queue=InMemoryQueue()
    )
    with pytest.raises(ApplicationError) as error:
        mcp.build_server()
    assert error.value.code == "SCHEMA_OUT_OF_DATE" and "ei db upgrade" in error.value.message


def test_running_builds_the_server_hands_it_to_the_runner_and_releases_the_database(
    database_url: str, process_state: None
) -> None:
    heard: list[Any] = []
    mcp = McpRuntime(
        AppSettings(database_url, BROKER, log_level="ERROR"),
        server=heard.append,
        queue=InMemoryQueue(),
    )
    mcp.run()
    assert set(tools_of(heard[0])) == READ
    assert logging.getLogger().level == logging.ERROR
    assert mcp._ledger is None and mcp._stores == []
    mcp.close()


def test_closing_releases_the_ledger_and_both_run_stores(database_url: str) -> None:
    mcp = runtime(database_url)
    mcp.build_server()
    assert mcp._ledger is not None
    engines = [mcp._ledger._engine, *(store._engine for store in mcp._stores)]
    assert len(engines) == 3
    pools = [engine.pool for engine in engines]
    mcp.close()
    mcp.close()
    # Disposing an engine replaces its connection pool, so a pool that is still the one it had was not released.
    assert all(engine.pool is not pool for engine, pool in zip(engines, pools, strict=True))


def test_the_database_is_released_even_when_the_server_crashes(
    database_url: str, process_state: None
) -> None:
    def crash(server: Any) -> None:
        raise RuntimeError("the host went away")

    mcp = McpRuntime(AppSettings(database_url, BROKER), server=crash, queue=InMemoryQueue())
    with pytest.raises(RuntimeError):
        mcp.run()
    assert mcp._ledger is None and mcp._stores == []


def test_the_default_runner_serves_over_stdio() -> None:
    class Server:
        def __init__(self) -> None:
            self.transport: list[str] = []

        def run(self, transport: str) -> None:
            self.transport.append(transport)

    server = Server()
    McpRuntime._stdio(server)
    assert server.transport == ["stdio"]


def exchange(process: subprocess.Popen[str], message: dict[str, Any]) -> dict[str, Any]:
    assert process.stdin is not None and process.stdout is not None
    process.stdin.write(json.dumps(message) + "\n")
    process.stdin.flush()
    return json.loads(process.stdout.readline())  # type: ignore[no-any-return]


def test_a_host_can_start_it_with_ei_serve_mcp_and_talk_to_it_over_stdio(
    tmp_path: Path, database_url: str
) -> None:
    seed(database_url)
    environment = {
        **os.environ,
        "EI_DATABASE_URL": database_url,
        "EI_RABBITMQ_URL": BROKER,
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    process = subprocess.Popen(
        [sys.executable, "-m", "engineering_influence", "serve", "mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
        cwd=tmp_path,
    )
    try:
        initialized = exchange(
            process,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            },
        )
        assert initialized["result"]["serverInfo"]["name"] == "engineering-influence"
        assert process.stdin is not None
        process.stdin.write(
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
        )
        process.stdin.flush()
        listed = exchange(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        assert {tool["name"] for tool in listed["result"]["tools"]} == READ
        called = exchange(
            process,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "get_run", "arguments": {"run_id": "run-1"}},
            },
        )
        assert called["result"]["isError"] is False
        assert "book/herbs.pdf" in json.dumps(called["result"])
    finally:
        process.terminate()
        process.communicate(timeout=20)
