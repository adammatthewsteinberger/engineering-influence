"""Listing, resuming and cancelling runs gives the same answer over the API, MCP and the SDK as the services do."""

import asyncio
from typing import Any

import httpx
import pytest
from engineering_influence_sdk import AsyncEngineeringInfluenceClient, EngineeringInfluenceClient
from fastapi.testclient import TestClient

from engineering_influence.contracts.run.v1.run_summary_v1 import RunSummaryV1
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
from engineering_influence.services.cancel_run import CancelRun
from engineering_influence.services.list_runs import ListRuns
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.resolve_spend_consent import ResolveSpendConsent
from engineering_influence.services.resume_run import ResumeRun
from engineering_influence.services.run_management import RunManagement
from engineering_influence.services.start_pipeline import StartPipeline


def seeded() -> tuple[InMemoryRunRepository, InMemoryQueue, RunManagement]:
    """A parked run, a running run and a completed run, saved the same way every time."""
    repo = InMemoryRunRepository()
    queue = InMemoryQueue()
    brief = BookBrief(BookKind.NONFICTION, "Windowsill herbs", 5_000_000)
    plan = NonfictionRecipes().plan()
    repo.save(BookRun("parked", brief, plan, Budget(cap=5_000_000)).start().park())
    repo.save(BookRun("running", brief, plan, Budget(cap=5_000_000)).start())
    last = plan.stages[-1]
    repo.save(BookRun("done", brief, plan, Budget(cap=5_000_000), stage=last).start().advance())
    manager = RunManagement(
        ListRuns(repo), ResumeRun(repo, queue), CancelRun(repo), ResolveSpendConsent(repo, queue)
    )
    return repo, queue, manager


def dump(run: Any) -> dict[str, Any]:
    return RunSummaryV1.from_run(run, []).model_dump(mode="json")


def expected_list() -> list[dict[str, Any]]:
    repo, _, _ = seeded()
    return [dump(run) for run in ListRuns(repo).runs()]


def expected_resume() -> dict[str, Any]:
    repo, queue, _ = seeded()
    return dump(ResumeRun(repo, queue).resume("parked"))


def expected_cancel() -> dict[str, Any]:
    repo, _, _ = seeded()
    return dump(CancelRun(repo).cancel("running"))


def api_for(api_guard: ApiGuard) -> TestClient:
    _, _, manager = seeded()
    app = ApiApplication(
        ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue())),
        api_guard,
        manager=manager,
    ).build()
    return TestClient(app)


def test_api_lists_runs_as_the_service_does(api_guard: ApiGuard, api_key: str) -> None:
    response = api_for(api_guard).get("/v1/runs", headers={"Authorization": f"Bearer {api_key}"})
    assert response.status_code == 200
    assert response.json() == expected_list()


def test_api_resumes_a_parked_run_as_the_service_does(api_guard: ApiGuard, api_key: str) -> None:
    response = api_for(api_guard).post(
        "/v1/runs/parked/resume", headers={"Authorization": f"Bearer {api_key}"}
    )
    assert response.status_code == 200
    assert response.json() == expected_resume()


def test_api_cancels_a_run_as_the_service_does(api_guard: ApiGuard, api_key: str) -> None:
    response = api_for(api_guard).post(
        "/v1/runs/running/cancel", headers={"Authorization": f"Bearer {api_key}"}
    )
    assert response.status_code == 200
    assert response.json() == expected_cancel()


def test_api_refuses_what_the_service_refuses(api_guard: ApiGuard, api_key: str) -> None:
    headers = {"Authorization": f"Bearer {api_key}"}
    client = api_for(api_guard)
    assert client.post("/v1/runs/absent/resume", headers=headers).status_code == 404
    assert client.post("/v1/runs/done/resume", headers=headers).status_code == 409
    assert client.post("/v1/runs/absent/cancel", headers=headers).status_code == 404


def test_run_management_needs_the_key(api_guard: ApiGuard) -> None:
    client = api_for(api_guard)
    assert client.get("/v1/runs").status_code == 401
    assert client.post("/v1/runs/parked/resume").status_code == 401
    assert client.post("/v1/runs/running/cancel").status_code == 401


def test_mcp_run_tools_match_the_service() -> None:
    _, _, manager = seeded()
    server: Any = McpApplication(
        ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue())), manager=manager
    ).build()
    tools = server._tool_manager._tools
    assert tools["list_runs"].fn() == expected_list()
    assert tools["resume_run"].fn("parked") == expected_resume()
    assert tools["cancel_run"].fn("running") == expected_cancel()


def test_mcp_has_no_run_tools_without_a_manager() -> None:
    server: Any = McpApplication(
        ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue()))
    ).build()
    assert not {"list_runs", "resume_run", "cancel_run"} & set(server._tool_manager._tools)


def sdk_for(api_guard: ApiGuard, api_key: str) -> EngineeringInfluenceClient:
    server = api_for(api_guard)

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

    return EngineeringInfluenceClient("http://local", api_key, httpx.MockTransport(handler))


def test_sdk_run_methods_match_the_service(api_guard: ApiGuard, api_key: str) -> None:
    client = sdk_for(api_guard, api_key)
    assert client.list_runs() == expected_list()
    assert client.resume_run("parked") == expected_resume()
    assert client.cancel_run("running") == expected_cancel()
    client.close()


def test_sdk_raises_for_a_refusal(api_guard: ApiGuard, api_key: str) -> None:
    client = sdk_for(api_guard, api_key)
    with pytest.raises(httpx.HTTPStatusError) as caught:
        client.resume_run("done")
    client.close()
    assert caught.value.response.status_code == 409


def test_the_async_sdk_run_methods_match_the_service(api_guard: ApiGuard, api_key: str) -> None:
    server = api_for(api_guard)

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

    async def call() -> tuple[Any, Any, Any]:
        client = AsyncEngineeringInfluenceClient(
            "http://local", api_key, httpx.MockTransport(handler)
        )
        try:
            return (
                await client.list_runs(),
                await client.resume_run("parked"),
                await client.cancel_run("running"),
            )
        finally:
            await client.close()

    assert asyncio.run(call()) == (expected_list(), expected_resume(), expected_cancel())


def test_the_async_sdk_raises_for_a_refusal(api_guard: ApiGuard, api_key: str) -> None:
    server = api_for(api_guard)

    def handler(request: httpx.Request) -> httpx.Response:
        forwarded = server.request(
            request.method,
            request.url.path,
            headers={"authorization": request.headers["authorization"]},
        )
        return httpx.Response(forwarded.status_code, json=forwarded.json(), request=request)

    async def call() -> None:
        client = AsyncEngineeringInfluenceClient(
            "http://local", api_key, httpx.MockTransport(handler)
        )
        try:
            await client.resume_run("done")
        finally:
            await client.close()

    with pytest.raises(httpx.HTTPStatusError) as caught:
        asyncio.run(call())
    assert caught.value.response.status_code == 409


def test_the_async_sdk_raises_when_the_list_is_refused(api_guard: ApiGuard) -> None:
    server = api_for(api_guard)

    def handler(request: httpx.Request) -> httpx.Response:
        forwarded = server.request(request.method, request.url.path)
        return httpx.Response(forwarded.status_code, json=forwarded.json(), request=request)

    async def call() -> None:
        client = AsyncEngineeringInfluenceClient(
            "http://local", "wrong", httpx.MockTransport(handler)
        )
        try:
            await client.list_runs()
        finally:
            await client.close()

    with pytest.raises(httpx.HTTPStatusError) as caught:
        asyncio.run(call())
    assert caught.value.response.status_code == 401
