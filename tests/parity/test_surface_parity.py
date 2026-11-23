"""Every interaction surface must return the same result for the same request."""

import contextlib
import io
import json
from typing import Any

import httpx
import pytest
from engineering_influence_sdk import EngineeringInfluenceClient
from fastapi.testclient import TestClient

from engineering_influence.contracts.brief.v1.book_brief_v1 import BookBriefV1
from engineering_influence.contracts.project_request import ProjectRequest
from engineering_influence.contracts.run.v1.run_summary_v1 import RunSummaryV1
from engineering_influence.controllers.project_controller import ProjectController
from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.interactions.api.api_guard import ApiGuard
from engineering_influence.interactions.api.application import ApiApplication
from engineering_influence.interactions.mcp.application import McpApplication
from engineering_influence.runtime.cli_runtime import CliRuntime
from engineering_influence.services.create_run import CreateRun
from engineering_influence.services.start_pipeline import StartPipeline

ARGS: dict[str, Any] = {
    "slug": "parity",
    "title": "Parity",
    "postulates": ["Evidence first."],
    "stages": ["thesis"],
}


def controller_result() -> dict[str, str]:
    request = ProjectRequest(
        **{**ARGS, "postulates": tuple(ARGS["postulates"]), "stages": tuple(ARGS["stages"])}
    )
    controller = ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue()))
    return controller.start(request).model_dump()


def test_api_matches_controller(api_guard: ApiGuard, api_key: str) -> None:
    app = ApiApplication(
        ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue())), api_guard
    ).build()
    response = TestClient(app).post(
        "/v1/pipelines", json=ARGS, headers={"Authorization": f"Bearer {api_key}"}
    )
    assert response.json() == controller_result()


def test_mcp_matches_controller() -> None:
    server: Any = McpApplication(
        ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue()))
    ).build()
    tool = server._tool_manager._tools["start_pipeline"]
    result = tool.fn(ARGS["slug"], ARGS["title"], ARGS["postulates"], ARGS["stages"])
    assert result == controller_result()


def test_cli_matches_controller() -> None:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        status = (
            CliRuntime()
            .build()
            .run(
                [
                    "pipeline",
                    "start",
                    "--slug",
                    "parity",
                    "--title",
                    "Parity",
                    "--postulate",
                    "Evidence first.",
                    "--stage",
                    "thesis",
                ]
            )
        )
    assert status == 0
    assert json.loads(buffer.getvalue()) == controller_result()


def test_sdk_matches_controller(api_guard: ApiGuard, api_key: str) -> None:
    server = TestClient(
        ApiApplication(
            ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue())), api_guard
        ).build()
    )

    def handler(request: httpx.Request) -> httpx.Response:
        forwarded = server.post(
            request.url.path,
            content=request.content,
            headers={
                "content-type": "application/json",
                "authorization": request.headers["authorization"],
            },
        )
        return httpx.Response(forwarded.status_code, json=forwarded.json(), request=request)

    client = EngineeringInfluenceClient("http://local", api_key, httpx.MockTransport(handler))
    result = client.start_pipeline("parity", "Parity", ("Evidence first.",), ("thesis",))
    client.close()
    assert result == controller_result()


BRIEF: dict[str, Any] = {
    "schema_version": 1,
    "kind": "nonfiction",
    "idea": "Windowsill herbs",
    "budget_micro_usd": 5_000_000,
}


def creator() -> CreateRun:
    return CreateRun(InMemoryRunRepository(), InMemoryQueue(), new_id=lambda: "parity-run")


def create_result() -> dict[str, Any]:
    run = creator().create(BookBriefV1.model_validate(BRIEF).to_model())
    return RunSummaryV1.from_run(run, []).model_dump(mode="json")


def test_api_creates_a_run_that_matches_the_service(api_guard: ApiGuard, api_key: str) -> None:
    app = ApiApplication(
        ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue())),
        api_guard,
        creator=creator(),
    ).build()
    response = TestClient(app).post(
        "/v1/runs", json=BRIEF, headers={"Authorization": f"Bearer {api_key}"}
    )
    assert response.status_code == 201
    assert response.json() == create_result()


def test_api_refuses_a_brief_that_is_not_one(api_guard: ApiGuard, api_key: str) -> None:
    app = ApiApplication(
        ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue())),
        api_guard,
        creator=creator(),
    ).build()
    response = TestClient(app).post(
        "/v1/runs", json={**BRIEF, "idea": "  "}, headers={"Authorization": f"Bearer {api_key}"}
    )
    assert response.status_code == 422


def test_api_run_creation_needs_the_key(api_guard: ApiGuard) -> None:
    app = ApiApplication(
        ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue())),
        api_guard,
        creator=creator(),
    ).build()
    assert TestClient(app).post("/v1/runs", json=BRIEF).status_code == 401


def test_mcp_creates_a_run_that_matches_the_service() -> None:
    server: Any = McpApplication(
        ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue())), creator()
    ).build()
    tool = server._tool_manager._tools["create_run"]
    assert tool.fn(BRIEF) == create_result()


def test_mcp_has_no_run_tool_without_a_creator() -> None:
    server: Any = McpApplication(
        ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue()))
    ).build()
    assert "create_run" not in server._tool_manager._tools


def test_sdk_creates_a_run_that_matches_the_service(api_guard: ApiGuard, api_key: str) -> None:
    server = TestClient(
        ApiApplication(
            ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue())),
            api_guard,
            creator=creator(),
        ).build()
    )

    def handler(request: httpx.Request) -> httpx.Response:
        forwarded = server.post(
            request.url.path,
            content=request.content,
            headers={
                "content-type": "application/json",
                "authorization": request.headers["authorization"],
            },
        )
        return httpx.Response(forwarded.status_code, json=forwarded.json(), request=request)

    client = EngineeringInfluenceClient("http://local", api_key, httpx.MockTransport(handler))
    result = client.create_run(BRIEF)
    client.close()
    assert result == create_result()


def test_without_a_creator_the_api_has_no_run_route(api_guard: ApiGuard, api_key: str) -> None:
    app = ApiApplication(
        ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue())), api_guard
    ).build()
    response = TestClient(app).post(
        "/v1/runs", json=BRIEF, headers={"Authorization": f"Bearer {api_key}"}
    )
    assert response.status_code == 404


def test_sdk_refuses_a_brief_the_service_refuses(api_guard: ApiGuard, api_key: str) -> None:
    server = TestClient(
        ApiApplication(
            ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue())),
            api_guard,
            creator=creator(),
        ).build()
    )

    def handler(request: httpx.Request) -> httpx.Response:
        forwarded = server.post(
            request.url.path,
            content=request.content,
            headers={
                "content-type": "application/json",
                "authorization": request.headers["authorization"],
            },
        )
        return httpx.Response(forwarded.status_code, json=forwarded.json(), request=request)

    client = EngineeringInfluenceClient("http://local", api_key, httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPStatusError) as caught:
        client.create_run({**BRIEF, "idea": "  "})
    client.close()
    assert caught.value.response.status_code == 422


def test_the_async_sdk_creates_a_run_that_matches_the_service(
    api_guard: ApiGuard, api_key: str
) -> None:
    import asyncio

    from engineering_influence_sdk import AsyncEngineeringInfluenceClient

    server = TestClient(
        ApiApplication(
            ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue())),
            api_guard,
            creator=creator(),
        ).build()
    )

    def handler(request: httpx.Request) -> httpx.Response:
        forwarded = server.post(
            request.url.path,
            content=request.content,
            headers={
                "content-type": "application/json",
                "authorization": request.headers["authorization"],
            },
        )
        return httpx.Response(forwarded.status_code, json=forwarded.json(), request=request)

    async def call() -> dict[str, Any]:
        client = AsyncEngineeringInfluenceClient(
            "http://local", api_key, httpx.MockTransport(handler)
        )
        try:
            return await client.create_run(BRIEF)
        finally:
            await client.close()

    assert asyncio.run(call()) == create_result()
