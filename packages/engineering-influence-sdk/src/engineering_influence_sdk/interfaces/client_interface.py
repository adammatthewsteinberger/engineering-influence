# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface of the synchronous engineering-influence client."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any


class EngineeringInfluenceClientInterface(ABC):
    """Small typed client with a stable pipeline-start operation."""

    __slots__ = ()

    @abstractmethod
    def start_pipeline(
        self,
        slug: str,
        title: str,
        postulates: tuple[str, ...],
        stages: tuple[str, ...],
    ) -> dict[str, str]:
        """Create a project and enqueue its first pipeline stage."""

    @abstractmethod
    def create_run(self, brief: Mapping[str, Any]) -> dict[str, Any]:
        """Start a book run from a brief (the brief contract v1); returns the new run."""

    @abstractmethod
    def list_runs(self) -> list[dict[str, Any]]:
        """Every saved book run, as run summaries."""

    @abstractmethod
    def resume_run(self, run_id: str) -> dict[str, Any]:
        """Un-park a parked run and queue its current stage."""

    @abstractmethod
    def grant_run(self, run_id: str, micro_usd: int | None = None) -> dict[str, Any]:
        """Give a run more budget and continue it."""

    @abstractmethod
    def deny_run(self, run_id: str) -> dict[str, Any]:
        """Refuse a run's request for more budget; it parks."""

    @abstractmethod
    def cancel_run(self, run_id: str) -> dict[str, Any]:
        """Stop a run for good."""

    @abstractmethod
    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
