# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Synchronous engineering-influence API client."""

from collections.abc import Mapping
from typing import Any, cast

import httpx

from engineering_influence_sdk.interfaces.client_interface import (
    EngineeringInfluenceClientInterface,
)


class EngineeringInfluenceClient(EngineeringInfluenceClientInterface):
    """Small typed client with a stable pipeline-start operation."""

    def __init__(self, base_url: str, api_key: str | None = None, transport: Any = None) -> None:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = httpx.Client(base_url=base_url, headers=headers, transport=transport)

    def start_pipeline(
        self,
        slug: str,
        title: str,
        postulates: tuple[str, ...],
        stages: tuple[str, ...],
    ) -> dict[str, str]:
        """Create a project and enqueue its first pipeline stage."""
        response = self._client.post(
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

    def create_run(self, brief: Mapping[str, Any]) -> dict[str, Any]:
        """Start a book run from a brief (the brief contract v1); returns the new run."""
        response = self._client.post("/v1/runs", json=dict(brief))
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    def list_runs(self) -> list[dict[str, Any]]:
        """Every saved book run, as run summaries."""
        response = self._client.get("/v1/runs")
        response.raise_for_status()
        return cast(list[dict[str, Any]], response.json())

    def resume_run(self, run_id: str) -> dict[str, Any]:
        """Un-park a parked run and queue its current stage."""
        response = self._client.post(f"/v1/runs/{run_id}/resume")
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    def cancel_run(self, run_id: str) -> dict[str, Any]:
        """Stop a run for good."""
        response = self._client.post(f"/v1/runs/{run_id}/cancel")
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()
