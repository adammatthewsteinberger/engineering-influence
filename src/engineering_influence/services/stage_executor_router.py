# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Sends each stage to the executor that knows how to do it."""

from collections.abc import Mapping

from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.stage_report import StageReport


class StageExecutorRouter(StageExecutorInterface):
    """A stage with its own executor goes there; every other stage goes to the default.

    Most stages are one prompt and one answer, which one executor does from a recipe. A stage that
    is a loop over the work (drafting chapters) is a different shape, and is named here.
    """

    def __init__(
        self, default: StageExecutorInterface, special: Mapping[str, StageExecutorInterface]
    ) -> None:
        """Remember the default executor and the executors for specific stages."""
        self._default = default
        self._special = dict(special)

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Run the stage with its own executor, or the default one."""
        return await self._special.get(run.stage, self._default).execute(run, attempt)
