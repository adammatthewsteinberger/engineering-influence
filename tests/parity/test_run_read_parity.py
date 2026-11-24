"""Reading a run and its files gives the same answer over the API, MCP and the SDK as the service does."""

import asyncio
import base64
from typing import Any

import httpx
import pytest
from engineering_influence_sdk import AsyncEngineeringInfluenceClient, EngineeringInfluenceClient
from fastapi.testclient import TestClient

from engineering_influence.controllers.project_controller import ProjectController
from engineering_influence.controllers.run_controller import RunController
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
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
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.read_run import ReadRun
from engineering_influence.services.start_pipeline import StartPipeline

TEXT = "# Brief\n\nWindowsill herbs, with a “quote” in it.\n".encode()
PDF = b"%PDF-1.7\n\xff\xfe\x00binary"
BIG = b"x" * (McpApplication.MAX_ARTIFACT_BYTES + 1)


def readers() -> RunController:
    runs, artifacts = InMemoryRunRepository(), InMemoryArtifactStore()
    brief = BookBrief(BookKind.NONFICTION, "Windowsill herbs", 5_000_000)
    runs.save(BookRun("run-1", brief, NonfictionRecipes().plan(), Budget(cap=5_000_000)).start())
    artifacts.put("run-1", "brief.md", TEXT)
    artifacts.put("run-1", "book/herbs.pdf", PDF)
    artifacts.put("run-1", "book/huge.bin", BIG)
    artifacts.put("run-1", "book/largest.txt", b"y" * McpApplication.MAX_ARTIFACT_BYTES)
    return RunController(ReadRun(runs, artifacts))


def expected_summary() -> dict[str, Any]:
    return readers().summary("run-1").model_dump(mode="json")


def api_for(api_guard: ApiGuard) -> TestClient:
    controller = ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue()))
    return TestClient(ApiApplication(controller, api_guard, runs=readers()).build())


def mcp_tools() -> dict[str, Any]:
    controller = ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue()))
    server: Any = McpApplication(controller, reader=readers()).build()
    return {name: tool.fn for name, tool in server._tool_manager._tools.items()}


def test_the_summary_names_the_artifacts_a_reader_can_then_fetch() -> None:
    assert expected_summary()["artifacts"] == [
        "book/herbs.pdf",
        "book/huge.bin",
        "book/largest.txt",
        "brief.md",
    ]


def test_mcp_gets_the_run_as_the_service_does() -> None:
    assert mcp_tools()["get_run"]("run-1") == expected_summary()


def test_mcp_reads_text_as_text_and_binary_as_base64() -> None:
    read = mcp_tools()["read_artifact"]
    assert read("run-1", "brief.md") == {
        "name": "brief.md",
        "bytes": len(TEXT),
        "encoding": "utf-8",
        "content": TEXT.decode(),
    }
    pdf = read("run-1", "book/herbs.pdf")
    assert (pdf["encoding"], pdf["bytes"]) == ("base64", len(PDF))
    assert base64.b64decode(pdf["content"]) == PDF


def test_mcp_refuses_a_file_too_large_to_return_and_says_where_to_download_it() -> None:
    with pytest.raises(ApplicationError) as error:
        mcp_tools()["read_artifact"]("run-1", "book/huge.bin")
    assert error.value.code == "ARTIFACT_TOO_LARGE"
    assert "GET /v1/runs/run-1/artifacts/book/huge.bin" in error.value.message


def test_mcp_returns_a_file_of_exactly_the_largest_size() -> None:
    result = mcp_tools()["read_artifact"]("run-1", "book/largest.txt")
    assert result["bytes"] == McpApplication.MAX_ARTIFACT_BYTES and result["encoding"] == "utf-8"


def test_mcp_refuses_what_the_service_refuses() -> None:
    tools = mcp_tools()
    with pytest.raises(ApplicationError) as missing_run:
        tools["get_run"]("nope")
    assert missing_run.value.code == "RUN_NOT_FOUND"
    with pytest.raises(ApplicationError) as missing_file:
        tools["read_artifact"]("run-1", "absent.md")
    assert missing_file.value.code == "ARTIFACT_NOT_FOUND"


def test_mcp_has_no_read_tools_without_a_reader() -> None:
    server: Any = McpApplication(
        ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue()))
    ).build()
    assert not {"get_run", "read_artifact"} & set(server._tool_manager._tools)


def bridge(api_guard: ApiGuard) -> Any:
    server = api_for(api_guard)

    def handler(request: httpx.Request) -> httpx.Response:
        forwarded = server.request(
            request.method,
            request.url.raw_path.decode(),
            headers={"authorization": request.headers["authorization"]},
        )
        return httpx.Response(
            forwarded.status_code,
            content=forwarded.content,
            headers={"content-type": forwarded.headers["content-type"]},
            request=request,
        )

    return httpx.MockTransport(handler)


def test_sdk_gets_the_run_and_downloads_its_files_byte_for_byte(
    api_guard: ApiGuard, api_key: str
) -> None:
    client = EngineeringInfluenceClient("http://local", api_key, bridge(api_guard))
    assert client.get_run("run-1") == expected_summary()
    assert client.get_artifact("run-1", "brief.md") == TEXT
    assert client.get_artifact("run-1", "book/herbs.pdf") == PDF
    assert client.get_artifact("run-1", "book/huge.bin") == BIG
    client.close()


def test_sdk_raises_for_a_run_or_file_that_is_not_there(api_guard: ApiGuard, api_key: str) -> None:
    client = EngineeringInfluenceClient("http://local", api_key, bridge(api_guard))
    with pytest.raises(httpx.HTTPStatusError) as no_run:
        client.get_run("nope")
    with pytest.raises(httpx.HTTPStatusError) as no_file:
        client.get_artifact("run-1", "absent.md")
    client.close()
    assert (no_run.value.response.status_code, no_file.value.response.status_code) == (404, 404)


def test_the_async_sdk_reads_the_same_way(api_guard: ApiGuard, api_key: str) -> None:
    async def call() -> tuple[Any, bytes, bytes]:
        client = AsyncEngineeringInfluenceClient("http://local", api_key, bridge(api_guard))
        try:
            return (
                await client.get_run("run-1"),
                await client.get_artifact("run-1", "book/herbs.pdf"),
                await client.get_artifact("run-1", "brief.md"),
            )
        finally:
            await client.close()

    assert asyncio.run(call()) == (expected_summary(), PDF, TEXT)


def test_the_async_sdk_raises_for_a_run_that_is_not_there(
    api_guard: ApiGuard, api_key: str
) -> None:
    async def call() -> None:
        client = AsyncEngineeringInfluenceClient("http://local", api_key, bridge(api_guard))
        try:
            await client.get_run("nope")
        finally:
            await client.close()

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(call())


def test_the_sdk_keeps_the_slashes_of_a_nested_name_and_escapes_everything_else() -> None:
    seen: list[bytes] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.raw_path)
        return httpx.Response(200, content=b"ok", request=request)

    client = EngineeringInfluenceClient("http://local", "k", httpx.MockTransport(record))
    assert client.get_artifact("run 1", "book/my herbs.pdf") == b"ok"
    client.close()

    async def call() -> None:
        later = AsyncEngineeringInfluenceClient("http://local", "k", httpx.MockTransport(record))
        try:
            await later.get_artifact("run 1", "book/my herbs.pdf")
        finally:
            await later.close()

    asyncio.run(call())
    assert seen == [b"/v1/runs/run%201/artifacts/book/my%20herbs.pdf"] * 2
