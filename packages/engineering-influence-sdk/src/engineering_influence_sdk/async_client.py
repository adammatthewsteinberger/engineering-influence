# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Asynchronous engineering-influence API client."""

from collections.abc import Mapping
from typing import Any, cast
from urllib.parse import quote

import httpx

from engineering_influence_sdk.interfaces.async_client_interface import (
    AsyncEngineeringInfluenceClientInterface,
)


class AsyncEngineeringInfluenceClient(AsyncEngineeringInfluenceClientInterface):
    """Async counterpart to the synchronous typed client."""

    def __init__(self, base_url: str, api_key: str | None = None, transport: Any = None) -> None:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = httpx.AsyncClient(base_url=base_url, headers=headers, transport=transport)

    async def start_pipeline(
        self,
        slug: str,
        title: str,
        postulates: tuple[str, ...],
        stages: tuple[str, ...],
    ) -> dict[str, str]:
        """Create a project and enqueue its first pipeline stage asynchronously."""
        response = await self._client.post(
            "/v1/pipelines",
            json={
                "slug": slug,
                "title": title,
                "postulates": list(postulates),
                "stages": list(stages),
            },
        )
        response.raise_for_status()
        return cast(dict[str, str], response.json())

    async def create_run(self, brief: Mapping[str, Any]) -> dict[str, Any]:
        """Start a book run from a brief (the brief contract v1) asynchronously; returns the new run."""
        response = await self._client.post("/v1/runs", json=dict(brief))
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    async def list_runs(self) -> list[dict[str, Any]]:
        """Every saved book run, as run summaries, asynchronously."""
        response = await self._client.get("/v1/runs")
        response.raise_for_status()
        return cast(list[dict[str, Any]], response.json())

    async def resume_run(self, run_id: str) -> dict[str, Any]:
        """Un-park a parked run and queue its current stage, asynchronously."""
        response = await self._client.post(f"/v1/runs/{run_id}/resume")
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    async def grant_run(self, run_id: str, micro_usd: int | None = None) -> dict[str, Any]:
        """Give a run more budget and continue it, asynchronously."""
        response = await self._client.post(
            f"/v1/runs/{run_id}/grant", json={"micro_usd": micro_usd}
        )
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    async def deny_run(self, run_id: str) -> dict[str, Any]:
        """Refuse a run's request for more budget, asynchronously."""
        response = await self._client.post(f"/v1/runs/{run_id}/deny")
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    async def cancel_run(self, run_id: str) -> dict[str, Any]:
        """Stop a run for good, asynchronously."""
        response = await self._client.post(f"/v1/runs/{run_id}/cancel")
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    async def get_run(self, run_id: str) -> dict[str, Any]:
        """A run's summary: its status, stage, budget and the names of the artifacts it has stored."""
        response = await self._client.get(f"/v1/runs/{quote(run_id, safe='')}")
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    async def get_artifact(self, run_id: str, name: str) -> bytes:
        """The bytes of one artifact a run stored, such as ``book/my-book.pdf``."""
        response = await self._client.get(
            f"/v1/runs/{quote(run_id, safe='')}/artifacts/{quote(name, safe='/')}"
        )
        response.raise_for_status()
        return response.content

    async def close(self) -> None:
        """Close the underlying async HTTP connection pool."""
        await self._client.aclose()
