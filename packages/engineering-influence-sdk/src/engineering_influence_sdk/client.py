"""Synchronous engineering-influence API client."""

from typing import Any, cast

import httpx


class EngineeringInfluenceClient:
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

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()
