# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ContextAssembler."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.assembled_context import AssembledContext
    from engineering_influence.models.context_plan import ContextPlan


class ContextAssemblerInterface(ABC):
    """Fit a drafting call's context into an input-token budget."""

    __slots__ = ()

    @abstractmethod
    def assemble(self, plan: ContextPlan, max_input_tokens: int) -> AssembledContext:
        """The fullest prompt that fits, or an ApplicationError when the fixed parts do not."""
