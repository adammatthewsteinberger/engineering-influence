# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Stage executor port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_run import BookRun
    from engineering_influence.models.stage_report import StageReport


class StageExecutorInterface(ABC):
    """Do the work of a run's current stage, safely repeatable."""

    __slots__ = ()

    @abstractmethod
    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Run ``run.stage`` and return what it found.

        The same stage may be executed more than once (a retry, or a redelivered message), so
        every model call goes through the run journal and every artifact is written once. Raise
        ``TransientStageError`` for a failure worth retrying and ``CapacityExhaustedError`` when
        credit or quota is gone; any other exception ends the run.
        """
