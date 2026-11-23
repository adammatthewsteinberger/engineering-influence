# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Starts a book run from a brief: saves it pending, then queues its first stage."""

import uuid
from collections.abc import Callable, Mapping

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.queue_interface import QueueInterface
from engineering_influence.interfaces.run_repository_interface import RunRepositoryInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.services.advance_run import AdvanceRun
from engineering_influence.services.interfaces.create_run_interface import CreateRunInterface


class CreateRun(CreateRunInterface):
    """A brief becomes a run whose budget is the brief's cap, and whose stages are the plan for its kind.

    The run is saved before its first stage is queued, as ``ResumeRun`` does, so a worker that picks the stage up
    always finds the run. A crash between the two leaves a pending run that is never queued; it can be found in
    ``run runs`` and queued with ``run resume``, which is why nothing here is lost. The run id is a fresh UUID, so
    two briefs never share one.
    """

    def __init__(
        self,
        runs: RunRepositoryInterface,
        queue: QueueInterface,
        plans: Mapping[BookKind, StagePlan],
        new_id: Callable[[], str] = lambda: uuid.uuid4().hex,
    ) -> None:
        self._runs = runs
        self._queue = queue
        self._plans = dict(plans)
        self._new_id = new_id

    def create(self, brief: BookBrief) -> BookRun:
        """Save a new pending run for the brief and queue its first stage; return the run."""
        plan = self._plans.get(brief.kind)
        if plan is None:
            raise ApplicationError(
                code="RUN_KIND_UNSUPPORTED",
                message=f"this build cannot start a {brief.kind.value} book",
                http_status=422,
            )
        run = BookRun(self._new_id(), brief, plan, Budget(cap=brief.budget_micro_usd))
        self._runs.save(run)
        self._queue.enqueue(
            AdvanceRun.KIND, {"run_id": run.run_id, "stage": run.stage, "attempt": 1}
        )
        return run
