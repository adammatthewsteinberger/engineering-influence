# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for CallModel."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.model_call_result import ModelCallResult
    from engineering_influence.models.model_request import ModelRequest
    from engineering_influence.services.interfaces.spend_guard_interface import (
        SpendGuardInterface,
    )


class CallModelInterface(ABC):
    """Make one model call that is replayed if it was made before and paid for if it was not."""

    __slots__ = ()

    @abstractmethod
    def call(
        self,
        guard: SpendGuardInterface,
        run_id: str,
        stage: str,
        attempt: int,
        request: ModelRequest,
    ) -> ModelCallResult:
        """Replay the journaled answer, or reserve, call, journal and settle."""
