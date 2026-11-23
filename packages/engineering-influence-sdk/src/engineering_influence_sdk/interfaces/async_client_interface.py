# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface of the asynchronous engineering-influence client."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any


class AsyncEngineeringInfluenceClientInterface(ABC):
    """Async counterpart to the synchronous typed client."""

    __slots__ = ()

    @abstractmethod
    async def create_run(self, brief: Mapping[str, Any]) -> dict[str, Any]:
        """Start a book run from a brief (the brief contract v1) asynchronously."""

    @abstractmethod
    async def list_runs(self) -> list[dict[str, Any]]:
        """Every saved book run, as run summaries, asynchronously."""

    @abstractmethod
    async def resume_run(self, run_id: str) -> dict[str, Any]:
        """Un-park a parked run and queue its current stage, asynchronously."""

    @abstractmethod
    async def cancel_run(self, run_id: str) -> dict[str, Any]:
        """Stop a run for good, asynchronously."""

    @abstractmethod
    async def start_pipeline(
        self,
        slug: str,
        title: str,
        postulates: tuple[str, ...],
        stages: tuple[str, ...],
    ) -> dict[str, str]:
        """Create a project and enqueue its first pipeline stage asynchronously."""

    @abstractmethod
    async def close(self) -> None:
        """Close the underlying async HTTP connection pool."""
