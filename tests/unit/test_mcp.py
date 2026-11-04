"""MCP tool contract tests."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock

from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.interaction.mcp.application import McpApplication


def test_mcp_exposes_start_pipeline_tool() -> None:
    server: Any = McpApplication(InMemoryLedger(), InMemoryQueue()).build()
    tool = server._tool_manager._tools["start_pipeline"]

    result = tool.fn(
        "demo",
        "Demo",
        ["Evidence first."],
        ["thesis"],
    )

    assert result == {"job_id": "local-job-1", "project_slug": "demo"}


def test_mcp_stdio_runner_delegates_to_server(monkeypatch: Any) -> None:
    application = McpApplication(InMemoryLedger(), InMemoryQueue())
    fake_server = type("FakeServer", (), {"run_stdio_async": AsyncMock()})()
    monkeypatch.setattr(application, "build", lambda: fake_server)

    asyncio.run(application.run_stdio())

    fake_server.run_stdio_async.assert_awaited_once_with()
