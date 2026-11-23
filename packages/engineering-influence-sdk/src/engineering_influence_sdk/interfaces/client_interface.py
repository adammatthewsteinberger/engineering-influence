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
    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
