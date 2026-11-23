# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Sends a run to the executor for its kind of book."""

from collections.abc import Mapping

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.stage_report import StageReport


class KindStageExecutor(StageExecutorInterface):
    """A non-fiction run and a novel run share stage names (brief, outline) but not recipes, so the kind picks first."""

    def __init__(self, by_kind: Mapping[BookKind, StageExecutorInterface]) -> None:
        self._by_kind = dict(by_kind)

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Run the stage with the executor for the brief's kind, or refuse a kind that has none."""
        executor = self._by_kind.get(run.brief.kind)
        if executor is None:
            raise ApplicationError(
                code="STAGE_KIND_UNSUPPORTED",
                message=f"this build has no stages for a {run.brief.kind.value} book",
                http_status=422,
            )
        return await executor.execute(run, attempt)
