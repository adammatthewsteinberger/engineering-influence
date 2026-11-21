# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for StageExecutorRuntime."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
    from engineering_influence.interfaces.journal_interface import JournalInterface
    from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface


class StageExecutorRuntimeInterface(ABC):
    """Chooses what does a run's stages, from the environment."""

    __slots__ = ()

    @abstractmethod
    def build(
        self, artifacts: ArtifactStoreInterface, journal: JournalInterface
    ) -> StageExecutorInterface:
        """The offline placeholder, or a model-backed executor when the environment opts in."""

    @abstractmethod
    def close(self) -> None:
        """Close the HTTP client behind a model-backed executor, if one was built."""
