"""The read routes: ``GET /v1/runs/{id}`` and ``GET /v1/runs/{id}/artifacts/{name}``."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from engineering_influence.controllers.project_controller import ProjectController
from engineering_influence.controllers.run_controller import RunController
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.interactions.api.api_guard import ApiGuard
from engineering_influence.interactions.api.application import ApiApplication
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.services.read_run import ReadRun
from engineering_influence.services.start_pipeline import StartPipeline

EPUB = bytes(range(256)) * 4


def build(guard: ApiGuard, with_runs: bool = True) -> TestClient:
    brief = BookBrief(kind=BookKind.NONFICTION, idea="sourdough", budget_micro_usd=1_000)
    plan = StagePlan(kind=BookKind.NONFICTION, stages=("brief", "outline"))
    runs, artifacts = InMemoryRunRepository(), InMemoryArtifactStore()
    runs.save(BookRun("run-1", brief, plan, Budget(cap=1_000), status=RunStatus.RUNNING))
    artifacts.put("run-1", "brief.md", b"# Brief")
    artifacts.put("run-1", "final/book.epub", EPUB)
    artifacts.put("run-2", "secret.md", b"someone else's run")
    controller = ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue()))
    run_controller = RunController(ReadRun(runs, artifacts)) if with_runs else None
    return TestClient(ApiApplication(controller, guard, runs=run_controller).build())


@pytest.fixture
def auth(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


def test_the_run_summary_is_json_in_the_versioned_shape(
    api_guard: ApiGuard, auth: dict[str, str]
) -> None:
    response = build(api_guard).get("/v1/runs/run-1", headers=auth)
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    assert (body["schema_version"], body["run_id"], body["status"]) == (1, "run-1", "running")
    assert (body["kind"], body["stage"], body["stages"]) == (
        "nonfiction",
        "brief",
        ["brief", "outline"],
    )
    assert body["artifacts"] == ["brief.md", "final/book.epub"]
    assert body["budget"]["remaining_micro_usd"] == 1_000
    assert "sourdough" not in response.text


def test_an_unknown_run_is_a_json_404(api_guard: ApiGuard, auth: dict[str, str]) -> None:
    response = build(api_guard).get("/v1/runs/nope", headers=auth)
    assert response.status_code == 404
    assert response.json() == {
        "code": "RUN_NOT_FOUND",
        "message": "no run 'nope'",
        "retryable": False,
    }


def test_an_artifact_downloads_byte_for_byte_and_cannot_be_sniffed_or_cached(
    api_guard: ApiGuard, auth: dict[str, str]
) -> None:
    response = build(api_guard).get("/v1/runs/run-1/artifacts/final/book.epub", headers=auth)
    assert response.status_code == 200
    assert response.content == EPUB
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "path",
    [
        "/v1/runs/run-1/artifacts/missing.md",
        "/v1/runs/run-9/artifacts/brief.md",
        "/v1/runs/run-1/artifacts/%2e%2e/run-2/secret.md",
        "/v1/runs/run-1/artifacts/..%2Frun-2%2Fsecret.md",
        "/v1/runs/run-1/artifacts/%5Cwindows",
    ],
)
def test_no_name_reaches_another_runs_artifacts(
    api_guard: ApiGuard, auth: dict[str, str], path: str
) -> None:
    response = build(api_guard).get(path, headers=auth)
    assert response.status_code == 404
    assert response.json()["code"] == "ARTIFACT_NOT_FOUND"
    assert b"someone else" not in response.content


@pytest.mark.parametrize("path", ["/v1/runs/run-1", "/v1/runs/run-1/artifacts/brief.md"])
def test_both_routes_need_the_api_key(api_guard: ApiGuard, path: str) -> None:
    client = build(api_guard)
    assert client.get(path).status_code == 401
    assert (
        client.get(path, headers={"Authorization": "Bearer wrong-key-0123456789abcdef"}).status_code
        == 401
    )


def test_without_a_run_controller_the_routes_do_not_exist(
    api_guard: ApiGuard, auth: dict[str, str]
) -> None:
    client = build(api_guard, with_runs=False)
    assert client.get("/v1/runs/run-1", headers=auth).status_code == 404
    assert client.get("/v1/runs/run-1/artifacts/brief.md", headers=auth).status_code == 404


def test_the_published_schema_lists_both_routes_and_the_summary_fields(
    api_guard: ApiGuard,
) -> None:
    schema = build(api_guard).app.openapi()  # type: ignore[attr-defined]
    assert "/v1/runs/{run_id}" in schema["paths"]
    assert "/v1/runs/{run_id}/artifacts/{name}" in schema["paths"]
    assert sorted(schema["components"]["schemas"]["RunSummaryV1"]["properties"]) == [
        "artifacts",
        "budget",
        "consent_requested_micro_usd",
        "issues",
        "kind",
        "run_id",
        "schema_version",
        "stage",
        "stages",
        "status",
    ]
