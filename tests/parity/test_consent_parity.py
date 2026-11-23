"""Granting and denying a run's request for budget does the same thing on every surface."""

import argparse
from typing import Any

import httpx
import pytest
from engineering_influence_sdk import EngineeringInfluenceClient
from fastapi.testclient import TestClient

from engineering_influence.contracts.run.v1.run_summary_v1 import RunSummaryV1
from engineering_influence.controllers.project_controller import ProjectController
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.interactions.api.api_guard import ApiGuard
from engineering_influence.interactions.api.application import ApiApplication
from engineering_influence.interactions.cli.run_cli import RunCli
from engineering_influence.interactions.mcp.application import McpApplication
from engineering_influence.models.spend_request import SpendRequest
from engineering_influence.services.brief_reader import BriefReader
from engineering_influence.services.cancel_run import CancelRun
from engineering_influence.services.create_run import CreateRun
from engineering_influence.services.list_runs import ListRuns
from engineering_influence.services.resolve_spend_consent import ResolveSpendConsent
from engineering_influence.services.resume_run import ResumeRun
from engineering_influence.services.run_management import RunManagement
from engineering_influence.services.run_progress import RunProgress
from engineering_influence.services.start_pipeline import StartPipeline

BRIEF_TOML = 'kind = "nonfiction"\nidea = "Windowsill herbs"\nbudget_micro_usd = 1000\n'
BRIEF_JSON: dict[str, Any] = {
    "kind": "nonfiction",
    "idea": "Windowsill herbs",
    "budget_micro_usd": 1000,
}


def waiting() -> tuple[InMemoryRunRepository, InMemoryQueue]:
    """The same run on every surface: created, started, and waiting for 700 micro-USD more."""
    repo, queue = InMemoryRunRepository(), InMemoryQueue()
    run = CreateRun(repo, queue, new_id=lambda: "run-1").create(
        BriefReader().read_text(BRIEF_TOML, "brief.toml")
    )
    repo.save(run.start().await_consent(SpendRequest(700, "brief")))
    queue.jobs.clear()
    return repo, queue


def summary(repo: InMemoryRunRepository) -> dict[str, Any]:
    run = repo.get("run-1")
    assert run is not None
    return RunSummaryV1.from_run(run, []).model_dump(mode="json")


def expected_grant() -> dict[str, Any]:
    repo, queue = waiting()
    ResolveSpendConsent(repo, queue).grant("run-1")
    return summary(repo)


def expected_deny() -> dict[str, Any]:
    repo, queue = waiting()
    ResolveSpendConsent(repo, queue).deny("run-1")
    return summary(repo)


def manager_for(repo: InMemoryRunRepository, queue: InMemoryQueue) -> RunManagement:
    return RunManagement(
        ListRuns(repo), ResumeRun(repo, queue), CancelRun(repo), ResolveSpendConsent(repo, queue)
    )


def api_for(api_guard: ApiGuard, manager: RunManagement) -> TestClient:
    app = ApiApplication(
        ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue())),
        api_guard,
        manager=manager,
    ).build()
    return TestClient(app)


def test_the_api_grants_like_the_service(api_guard: ApiGuard, api_key: str) -> None:
    repo, queue = waiting()
    response = api_for(api_guard, manager_for(repo, queue)).post(
        "/v1/runs/run-1/grant", json={}, headers={"Authorization": f"Bearer {api_key}"}
    )
    assert response.status_code == 200 and response.json() == expected_grant()
    assert summary(repo) == expected_grant()


def test_mcp_grants_like_the_service() -> None:
    repo, queue = waiting()
    server: Any = McpApplication(
        ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue())),
        manager=manager_for(repo, queue),
    ).build()
    assert server._tool_manager._tools["grant_run"].fn("run-1", None) == expected_grant()
    assert summary(repo) == expected_grant()


def test_sdk_grants_like_the_service(api_guard: ApiGuard, api_key: str) -> None:
    repo, queue = waiting()
    server = api_for(api_guard, manager_for(repo, queue))

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
    assert client.grant_run("run-1") == expected_grant()
    client.close()
    assert summary(repo) == expected_grant()


def test_the_command_line_grants_like_the_service(capsys: pytest.CaptureFixture[str]) -> None:
    repo, queue = waiting()
    cli = RunCli(
        lambda: None,
        lambda: None,
        lambda: None,
        lambda: None,
        lambda: None,
        lambda: None,  # type: ignore[arg-type,return-value]
        BriefReader(),
        lambda: ResolveSpendConsent(repo, queue),
    )
    assert cli.run(argparse.Namespace(run_command="grant", run_id="run-1", micro_usd=None)) == 0
    assert summary(repo) == expected_grant()


def test_acp_grants_like_the_service_when_the_client_selects_grant() -> None:
    from engineering_influence.interactions.acp.application import AcpApplication as Acp

    repo, queue = waiting()
    agent = Acp(
        CreateRun(repo, queue, new_id=lambda: "run-1"),
        CancelRun(repo),
        BriefReader(),
        RunProgress(repo),
        ResolveSpendConsent(repo, queue),
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
    # The run is waiting; the follower asks the client, and the client selects grant.
    repo.save(repo.get("run-1").start().await_consent(SpendRequest(700, "brief")))  # type: ignore[union-attr]
    [request] = [
        m for m in agent.follow_messages() if m.get("method") == "session/request_permission"
    ]
    agent.handle(
        {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {"outcome": {"outcome": "selected", "optionId": "grant"}},
        }
    )
    assert summary(repo) == expected_grant()


def test_every_surface_denies_like_the_service(api_guard: ApiGuard, api_key: str) -> None:
    repo, queue = waiting()
    response = api_for(api_guard, manager_for(repo, queue)).post(
        "/v1/runs/run-1/deny", headers={"Authorization": f"Bearer {api_key}"}
    )
    assert response.json() == expected_deny() and summary(repo) == expected_deny()
    assert queue.jobs == []


def test_every_surface_refuses_a_grant_for_a_run_that_is_not_waiting(
    api_guard: ApiGuard, api_key: str, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, queue = waiting()
    ResolveSpendConsent(repo, queue).deny("run-1")
    parked = summary(repo)
    api = api_for(api_guard, manager_for(repo, queue)).post(
        "/v1/runs/run-1/grant", json={}, headers={"Authorization": f"Bearer {api_key}"}
    )
    assert api.status_code == 409
    with pytest.raises(ApplicationError) as mcp:
        server: Any = McpApplication(
            ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue())),
            manager=manager_for(repo, queue),
        ).build()
        server._tool_manager._tools["grant_run"].fn("run-1", None)
    assert mcp.value.code == "CONSENT_NOT_PENDING"
    cli = RunCli(
        lambda: None,
        lambda: None,
        lambda: None,
        lambda: None,
        lambda: None,
        lambda: None,  # type: ignore[arg-type,return-value]
        BriefReader(),
        lambda: ResolveSpendConsent(repo, queue),
    )
    assert cli.run(argparse.Namespace(run_command="grant", run_id="run-1", micro_usd=None)) == 1
    assert summary(repo) == parked
    assert queue.jobs == []
