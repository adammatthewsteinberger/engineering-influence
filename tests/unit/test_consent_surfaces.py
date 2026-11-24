"""Granting and denying a run's request for budget works through the API, MCP and the SDK, and refuses what the service refuses."""

import asyncio
from typing import Any

import httpx
from engineering_influence_sdk import AsyncEngineeringInfluenceClient, EngineeringInfluenceClient
from fastapi.testclient import TestClient

from engineering_influence.controllers.project_controller import ProjectController
from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.interactions.api.api_guard import ApiGuard
from engineering_influence.interactions.api.application import ApiApplication
from engineering_influence.interactions.mcp.application import McpApplication
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.spend_request import SpendRequest
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.services.cancel_run import CancelRun
from engineering_influence.services.list_runs import ListRuns
from engineering_influence.services.resolve_spend_consent import ResolveSpendConsent
from engineering_influence.services.resume_run import ResumeRun
from engineering_influence.services.run_management import RunManagement
from engineering_influence.services.start_pipeline import StartPipeline


def waiting_store() -> tuple[InMemoryRunRepository, InMemoryQueue, RunManagement]:
    repo, queue = InMemoryRunRepository(), InMemoryQueue()
    brief = BookBrief(BookKind.NONFICTION, "Windowsill herbs", 1_000)
    plan = StagePlan(kind=BookKind.NONFICTION, stages=("brief", "outline"))
    repo.save(
        BookRun("run-1", brief, plan, Budget(cap=1_000))
        .start()
        .await_consent(SpendRequest(700, "brief"))
    )
    manager = RunManagement(
        ListRuns(repo), ResumeRun(repo, queue), CancelRun(repo), ResolveSpendConsent(repo, queue)
    )
    return repo, queue, manager


def api_for(api_guard: ApiGuard, manager: RunManagement) -> TestClient:
    app = ApiApplication(
        ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue())),
        api_guard,
        manager=manager,
    ).build()
    return TestClient(app)


def test_the_api_grants_the_amount_a_run_asked_for(api_guard: ApiGuard, api_key: str) -> None:
    _, queue, manager = waiting_store()
    response = api_for(api_guard, manager).post(
        "/v1/runs/run-1/grant", json={}, headers={"Authorization": f"Bearer {api_key}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert response.json()["budget"]["cap_micro_usd"] == 1_700
    assert response.json()["consent_requested_micro_usd"] is None
    assert [job[1]["stage"] for job in queue.jobs] == ["brief"]


def test_the_api_denies_a_request_and_the_run_parks(api_guard: ApiGuard, api_key: str) -> None:
    _, queue, manager = waiting_store()
    response = api_for(api_guard, manager).post(
        "/v1/runs/run-1/deny", headers={"Authorization": f"Bearer {api_key}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "parked_capacity"
    assert queue.jobs == []


def test_the_api_refuses_a_grant_for_a_different_amount(api_guard: ApiGuard, api_key: str) -> None:
    _, queue, manager = waiting_store()
    response = api_for(api_guard, manager).post(
        "/v1/runs/run-1/grant",
        json={"micro_usd": 900},
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert response.status_code == 409
    assert queue.jobs == []


def test_the_api_refuses_a_body_it_does_not_know(api_guard: ApiGuard, api_key: str) -> None:
    _, _, manager = waiting_store()
    response = api_for(api_guard, manager).post(
        "/v1/runs/run-1/grant",
        json={"micro_usd": 5, "mood": "grim"},
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert response.status_code == 422


def test_grant_and_deny_need_the_key(api_guard: ApiGuard) -> None:
    _, _, manager = waiting_store()
    client = api_for(api_guard, manager)
    assert client.post("/v1/runs/run-1/grant", json={}).status_code == 401
    assert client.post("/v1/runs/run-1/deny").status_code == 401


def mcp_tools(manager: RunManagement) -> Any:
    server: Any = McpApplication(
        ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue())),
        manager=manager,
        allow_spend=True,
    ).build()
    return server._tool_manager._tools


def test_mcp_grants_a_waiting_run_like_the_service() -> None:
    _, _, manager = waiting_store()
    assert mcp_tools(manager)["grant_run"].fn("run-1", None)["status"] == "running"


def test_mcp_denies_a_waiting_run_like_the_service() -> None:
    _, _, manager = waiting_store()
    assert mcp_tools(manager)["deny_run"].fn("run-1")["status"] == "parked_capacity"


def test_the_sdk_grants_and_denies_through_the_api(api_guard: ApiGuard, api_key: str) -> None:
    _, _, manager = waiting_store()
    server = api_for(api_guard, manager)

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
    assert client.deny_run("run-1")["status"] == "parked_capacity"
    assert client.grant_run("run-1", 300)["status"] == "running"
    client.close()


def test_the_async_sdk_grants_and_denies_through_the_api(api_guard: ApiGuard, api_key: str) -> None:
    _, _, manager = waiting_store()
    server = api_for(api_guard, manager)

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

    async def call() -> tuple[dict[str, Any], dict[str, Any]]:
        client = AsyncEngineeringInfluenceClient(
            "http://local", api_key, httpx.MockTransport(handler)
        )
        try:
            return await client.deny_run("run-1"), await client.grant_run("run-1", 300)
        finally:
            await client.close()

    denied, granted = asyncio.run(call())
    assert denied["status"] == "parked_capacity"
    assert granted["status"] == "running"
