# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for RunController."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.contracts.run.v1.run_summary_v1 import RunSummaryV1


class RunControllerInterface(ABC):
    """Transport-neutral read access to book runs."""

    __slots__ = ()

    @abstractmethod
    def summary(self, run_id: str) -> RunSummaryV1:
        """Describe a run for an API or a command line."""

    @abstractmethod
    def artifact(self, run_id: str, name: str) -> bytes:
        """The bytes of one stored artifact."""
