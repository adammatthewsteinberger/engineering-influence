"""MCP tool contract tests."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock

from engineering_influence.controllers.project_controller import ProjectController
from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.interactions.mcp.application import McpApplication
from engineering_influence.services.start_pipeline import StartPipeline


def test_mcp_exposes_start_pipeline_tool() -> None:
    server: Any = McpApplication(
        ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue()))
    ).build()
    tool = server._tool_manager._tools["start_pipeline"]

    result = tool.fn(
        "demo",
        "Demo",
        ["Evidence first."],
        ["thesis"],
    )

    assert result == {"job_id": "local-job-1", "project_slug": "demo"}


def test_mcp_stdio_runner_delegates_to_server() -> None:
    fake_server = type("FakeServer", (), {"run_stdio_async": AsyncMock()})()

    class ApplicationWithFakeServer(McpApplication):
        def build(self) -> Any:
            return fake_server

    application = ApplicationWithFakeServer(
        ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue()))
    )

    asyncio.run(application.run_stdio())

    fake_server.run_stdio_async.assert_awaited_once_with()


def test_a_server_built_without_spend_does_not_offer_to_grant_or_deny_budget() -> None:
    from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
    from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
    from engineering_influence.infrastructure.in_memory_run_repository import (
        InMemoryRunRepository,
    )
    from engineering_influence.services.cancel_run import CancelRun
    from engineering_influence.services.list_runs import ListRuns
    from engineering_influence.services.resolve_spend_consent import ResolveSpendConsent
    from engineering_influence.services.resume_run import ResumeRun
    from engineering_influence.services.run_management import RunManagement

    repo, queue = InMemoryRunRepository(), InMemoryQueue()
    manager = RunManagement(
        ListRuns(repo), ResumeRun(repo, queue), CancelRun(repo), ResolveSpendConsent(repo, queue)
    )
    controller = ProjectController(StartPipeline(InMemoryLedger(), queue))
    careful = set(McpApplication(controller, manager=manager).build()._tool_manager._tools)
    trusting = set(
        McpApplication(controller, manager=manager, allow_spend=True).build()._tool_manager._tools
    )
    assert careful == {"start_pipeline", "list_runs", "resume_run", "cancel_run"}
    assert trusting - careful == {"grant_run", "deny_run"}


def creating(ceiling: int | None) -> Any:
    from engineering_influence.infrastructure.in_memory_run_repository import (
        InMemoryRunRepository,
    )
    from engineering_influence.services.create_run import CreateRun

    repo, queue = InMemoryRunRepository(), InMemoryQueue()
    controller = ProjectController(StartPipeline(InMemoryLedger(), queue))
    app = McpApplication(controller, CreateRun(repo, queue), max_run_budget_micro_usd=ceiling)
    return app.build()._tool_manager._tools["create_run"].fn, repo


def brief(budget: int) -> dict[str, Any]:
    return {"schema_version": 1, "kind": "novel", "idea": "A road", "budget_micro_usd": budget}


def test_a_run_started_over_mcp_cannot_have_a_bigger_cap_than_the_operator_allows() -> None:
    import pytest

    from engineering_influence.errors.application_error import ApplicationError

    create, repo = creating(2_000_000)
    assert create(brief(2_000_000))["budget"]["cap_micro_usd"] == 2_000_000
    with pytest.raises(ApplicationError) as error:
        create(brief(2_000_001))
    assert error.value.code == "BUDGET_ABOVE_LIMIT" and error.value.http_status == 422
    assert "2000000" in error.value.message and "2000001" in error.value.message
    assert len(repo.run_ids()) == 1


def test_a_server_built_without_a_ceiling_takes_any_budget() -> None:
    create, _ = creating(None)
    assert create(brief(900_000_000))["budget"]["cap_micro_usd"] == 900_000_000
