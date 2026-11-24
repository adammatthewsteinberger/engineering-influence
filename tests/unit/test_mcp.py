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
    careful = set(
        McpApplication(controller, manager=manager, allow_spend=False).build()._tool_manager._tools
    )
    trusting = set(McpApplication(controller, manager=manager).build()._tool_manager._tools)
    assert careful == {"start_pipeline", "list_runs", "resume_run", "cancel_run"}
    assert trusting - careful == {"grant_run", "deny_run"}
