"""Every interaction surface must return the same result for the same request."""

import contextlib
import io
import json
from typing import Any

import httpx
from engineering_influence_sdk import EngineeringInfluenceClient
from fastapi.testclient import TestClient

from engineering_influence.contracts.project_request import ProjectRequest
from engineering_influence.controllers.project_controller import ProjectController
from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.interaction.api.application import ApiApplication
from engineering_influence.interaction.cli.main import CliApplication
from engineering_influence.interaction.mcp.application import McpApplication
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


def test_api_matches_controller() -> None:
    app = ApiApplication(InMemoryLedger(), InMemoryQueue()).build()
    assert TestClient(app).post("/v1/pipelines", json=ARGS).json() == controller_result()


def test_mcp_matches_controller() -> None:
    server: Any = McpApplication(InMemoryLedger(), InMemoryQueue()).build()
    tool = server._tool_manager._tools["start_pipeline"]
    result = tool.fn(ARGS["slug"], ARGS["title"], ARGS["postulates"], ARGS["stages"])
    assert result == controller_result()


def test_cli_matches_controller() -> None:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        status = CliApplication().run(
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
    assert status == 0
    assert json.loads(buffer.getvalue()) == controller_result()


def test_sdk_matches_controller() -> None:
    server = TestClient(ApiApplication(InMemoryLedger(), InMemoryQueue()).build())

    def handler(request: httpx.Request) -> httpx.Response:
        forwarded = server.post(
            request.url.path, content=request.content, headers={"content-type": "application/json"}
        )
        return httpx.Response(forwarded.status_code, json=forwarded.json(), request=request)

    client = EngineeringInfluenceClient("http://local", None, httpx.MockTransport(handler))
    result = client.start_pipeline("parity", "Parity", ("Evidence first.",), ("thesis",))
    client.close()
    assert result == controller_result()
