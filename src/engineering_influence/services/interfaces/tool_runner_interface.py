# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ToolRunner."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Collection
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.tool_call import ToolCall
    from engineering_influence.models.tool_result import ToolResult


class ToolRunnerInterface(ABC):
    """Runs the calls a model asked for, within the tools a stage was given."""

    __slots__ = ()

    @abstractmethod
    def run(
        self,
        run_id: str,
        stage: str,
        attempt: int,
        call: ToolCall,
        offered: Collection[str],
        evidence: str,
    ) -> ToolResult:
        """The result of the call, replayed from the journal if this run already made it.

        ``evidence`` is the text the model has been legitimately shown so far (the stage's prompt
        and the earlier tool results), against which a tool can check where its arguments came from.
        """

    @abstractmethod
    def close(self) -> None:
        """Stop accepting calls and let the threads that run tools finish."""
