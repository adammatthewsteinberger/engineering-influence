"""Sync and async SDK contract tests."""

import asyncio
import json

import httpx
from engineering_influence_sdk import AsyncEngineeringInfluenceClient, EngineeringInfluenceClient


def transport(request: httpx.Request) -> httpx.Response:
    assert request.url.path == "/v1/pipelines"
    assert request.headers["Authorization"] == "Bearer test-key"
    assert json.loads(request.content)["slug"] == "demo"
    return httpx.Response(200, json={"job_id": "job-1", "project_slug": "demo"}, request=request)


def test_sync_sdk_starts_pipeline() -> None:
    client = EngineeringInfluenceClient(
        "https://example.test", "test-key", httpx.MockTransport(transport)
    )

    assert client.start_pipeline("demo", "Demo", ("Evidence.",), ("thesis",)) == {
        "job_id": "job-1",
        "project_slug": "demo",
    }
    client.close()


def test_async_sdk_starts_pipeline() -> None:
    async def run() -> None:
        client = AsyncEngineeringInfluenceClient(
            "https://example.test", "test-key", httpx.MockTransport(transport)
        )

        assert await client.start_pipeline("demo", "Demo", ("Evidence.",), ("thesis",)) == {
            "job_id": "job-1",
            "project_slug": "demo",
        }
        await client.close()

    asyncio.run(run())
