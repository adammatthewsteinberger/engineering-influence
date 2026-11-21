# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for AskModel."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.model_answer import ModelAnswer
    from engineering_influence.models.model_request import ModelRequest
    from engineering_influence.services.interfaces.spend_guard_interface import (
        SpendGuardInterface,
    )


class AskModelInterface(ABC):
    """Ask a model until it gives a complete answer or the bounded attempts run out."""

    __slots__ = ()

    @abstractmethod
    def ask(
        self,
        guard: SpendGuardInterface,
        run_id: str,
        stage: str,
        attempt: int,
        request: ModelRequest,
    ) -> ModelAnswer:
        """A complete answer, replayed or got live; otherwise the best text and the issues."""
