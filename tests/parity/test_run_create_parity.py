"""Starting a run from a brief stores the same run and answers the same over every surface."""

import argparse
from pathlib import Path
from typing import Any

import httpx
from engineering_influence_sdk import EngineeringInfluenceClient
from fastapi.testclient import TestClient

from engineering_influence.contracts.run.v1.run_summary_v1 import RunSummaryV1
from engineering_influence.controllers.project_controller import ProjectController
from engineering_influence.infrastructure.in_memory_acp_session_store import InMemoryAcpSessionStore
from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.interactions.acp.application import AcpApplication
from engineering_influence.interactions.api.api_guard import ApiGuard
from engineering_influence.interactions.api.application import ApiApplication
from engineering_influence.interactions.cli.run_cli import RunCli
from engineering_influence.interactions.mcp.application import McpApplication
from engineering_influence.models.run_status import RunStatus
from engineering_influence.services.brief_reader import BriefReader
from engineering_influence.services.cancel_run import CancelRun
from engineering_influence.services.create_run import CreateRun
from engineering_influence.services.resolve_spend_consent import ResolveSpendConsent
from engineering_influence.services.run_progress import RunProgress
from engineering_influence.services.start_pipeline import StartPipeline

BRIEF_TOML = 'kind = "nonfiction"\nidea = "Windowsill herbs"\nbudget_micro_usd = 5000000\n'
BRIEF_JSON: dict[str, Any] = {
    "kind": "nonfiction",
    "idea": "Windowsill herbs",
    "budget_micro_usd": 5000000,
}


def fresh() -> tuple[InMemoryRunRepository, InMemoryQueue]:
    return InMemoryRunRepository(), InMemoryQueue()


def creator(repo: InMemoryRunRepository, queue: InMemoryQueue) -> CreateRun:
    return CreateRun(repo, queue, new_id=lambda: "run-1")


def summary(repo: InMemoryRunRepository) -> dict[str, Any]:
    run = repo.get("run-1")
    assert run is not None
    return RunSummaryV1.from_run(run, []).model_dump(mode="json")


def expected() -> dict[str, Any]:
    """What the service stores and answers when it is called directly: the reference for every surface."""
    repo, queue = fresh()
    creator(repo, queue).create(BriefReader().read_text(BRIEF_TOML, "brief.toml"))
    stored = summary(repo)
    assert stored["status"] == RunStatus.PENDING.value
    return stored


def unused() -> Any:
    """The services a create does not use; reaching one is a test failure."""
    raise AssertionError("this surface should only create a run")


def controller() -> ProjectController:
    return ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue()))


def test_api_starts_the_same_run(api_guard: ApiGuard, api_key: str) -> None:
    repo, queue = fresh()
    app = ApiApplication(controller(), api_guard, creator=creator(repo, queue)).build()
    response = TestClient(app).post(
        "/v1/runs", json=BRIEF_JSON, headers={"Authorization": f"Bearer {api_key}"}
    )
    assert response.status_code == 201
    assert response.json() == expected()
    assert summary(repo) == expected()


def test_mcp_starts_the_same_run() -> None:
    repo, queue = fresh()
    server: Any = McpApplication(controller(), creator=creator(repo, queue)).build()
    assert server._tool_manager._tools["create_run"].fn(BRIEF_JSON) == expected()
    assert summary(repo) == expected()


def test_sdk_starts_the_same_run(api_guard: ApiGuard, api_key: str) -> None:
    repo, queue = fresh()
    server = TestClient(
        ApiApplication(controller(), api_guard, creator=creator(repo, queue)).build()
    )

    def handler(request: httpx.Request) -> httpx.Response:
        forwarded = server.request(
            request.method,
            request.url.path,
            content=request.content,
            headers={
                "content-type": "application/json",
                "authorization": request.headers["authorization"],
            },
        )
        return httpx.Response(forwarded.status_code, json=forwarded.json(), request=request)

    client = EngineeringInfluenceClient("http://local", api_key, httpx.MockTransport(handler))
    assert client.create_run(BRIEF_JSON) == expected()
    client.close()
    assert summary(repo) == expected()


def test_acp_prompt_starts_the_same_run() -> None:
    repo, queue = fresh()
    agent = AcpApplication(
        creator(repo, queue),
        CancelRun(repo),
        BriefReader(),
        RunProgress(repo),
        ResolveSpendConsent(repo, queue),
        InMemoryAcpSessionStore(),
    )
    session = agent.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "session/new", "params": {"cwd": "/work"}}
    )
    session_id = session[0]["result"]["sessionId"]
    agent.handle(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "session/prompt",
            "params": {"sessionId": session_id, "prompt": [{"type": "text", "text": BRIEF_TOML}]},
        }
    )
    assert summary(repo) == expected()


def test_the_command_line_starts_the_same_run(tmp_path: Path) -> None:
    repo, queue = fresh()
    brief = tmp_path / "brief.toml"
    brief.write_text(BRIEF_TOML, encoding="utf-8")
    cli = RunCli(
        unused, unused, unused, unused, lambda: creator(repo, queue), unused, BriefReader(), unused
    )
    assert cli.run(argparse.Namespace(run_command="create", brief=brief)) == 0
    assert summary(repo) == expected()
