# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for RunToolLoop."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.model_request import ModelRequest
    from engineering_influence.models.tool_loop_result import ToolLoopResult
    from engineering_influence.services.interfaces.spend_guard_interface import (
        SpendGuardInterface,
    )


class RunToolLoopInterface(ABC):
    """Asks a model, runs the tools it calls, and asks again until it has an answer."""

    __slots__ = ()

    @abstractmethod
    def run(
        self,
        guard: SpendGuardInterface,
        run_id: str,
        stage: str,
        attempt: int,
        request: ModelRequest,
    ) -> ToolLoopResult:
        """The loop's outcome: the final text, or the best it got and the issues."""
