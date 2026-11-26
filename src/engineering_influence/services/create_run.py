# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Starts a book run from a brief: saves it pending, then queues its first stage."""

import uuid
from collections.abc import Callable, Mapping
from contextlib import nullcontext
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.queue_interface import QueueInterface
from engineering_influence.interfaces.run_repository_interface import RunRepositoryInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.source_entry import SourceEntry
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.services.advance_run import AdvanceRun
from engineering_influence.services.interfaces.create_run_interface import CreateRunInterface
from engineering_influence.services.interfaces.spend_ceiling_interface import (
    SpendCeilingInterface,
)
from engineering_influence.services.lock_shooting_script_stage_executor import (
    LockShootingScriptStageExecutor,
)
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.novel_recipes import NovelRecipes
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes


class CreateRun(CreateRunInterface):
    """A brief becomes a run whose budget is the brief's cap, and whose stages are the plan for its kind.

    The run is saved before its first stage is queued, as ``ResumeRun`` does, so a worker that picks the stage up
    always finds the run. A crash between the two leaves a pending run that is never queued; it can be found in
    ``run runs`` and queued with ``run resume``, which is why nothing here is lost. The run id is a fresh UUID, so
    two briefs never share one. With a spend ceiling, a brief whose cap would break the operator's limits is refused
    before anything is saved or queued.
    """

    PLANS: ClassVar[Mapping[BookKind, StagePlan]] = {
        BookKind.NONFICTION: NonfictionRecipes().plan(),
        BookKind.NOVEL: NovelRecipes().plan(),
        BookKind.SCREENPLAY: ScreenplayRecipes().plan(),
    }

    def __init__(
        self,
        runs: RunRepositoryInterface,
        queue: QueueInterface,
        plans: Mapping[BookKind, StagePlan] | None = None,
        new_id: Callable[[], str] = lambda: uuid.uuid4().hex,
        ceiling: SpendCeilingInterface | None = None,
        artifacts: ArtifactStoreInterface | None = None,
    ) -> None:
        self._runs = runs
        self._queue = queue
        self._plans = dict(self.PLANS if plans is None else plans)
        self._new_id = new_id
        self._ceiling = ceiling
        self._artifacts = artifacts

    def _store_sources(self, run_id: str, sources: tuple[SourceEntry, ...]) -> None:
        """Write each source as its artifact before the run is saved, so a run never starts without its sources."""
        if self._artifacts is None:
            return
        for entry in sources:
            self._artifacts.put(run_id, entry.artifact(), entry.text.encode("utf-8"))

    def create(
        self,
        brief: BookBrief,
        sources: tuple[SourceEntry, ...] = (),
        previous_lock: str | None = None,
    ) -> BookRun:
        """Save a new pending run for the brief and queue its first stage; return the run. A previous shooting script
        lock, when given, is kept as the run's previous lock, so the run's scene numbers carry over from it."""
        plan = self._plans.get(brief.kind)
        if plan is None:
            raise ApplicationError(
                code="RUN_KIND_UNSUPPORTED",
                message=f"this build cannot start a {brief.kind.value} book",
                http_status=422,
            )
        if brief.kind is BookKind.SCREENPLAY and not sources:
            raise ApplicationError(
                code="SCREENPLAY_NO_SOURCES",
                message="a screenplay run needs a source folder, given with --source",
                http_status=422,
            )
        if previous_lock is not None and brief.kind is not BookKind.SCREENPLAY:
            raise ApplicationError(
                code="RUN_KIND_UNSUPPORTED",
                message="a shooting script lock is for screenplay runs only",
                http_status=422,
            )
        if (sources or previous_lock is not None) and self._artifacts is None:
            raise ApplicationError(
                code="SOURCES_NOT_STORED",
                message="this build cannot keep source files for a run",
                http_status=500,
            )
        with nullcontext() if self._ceiling is None else self._ceiling.hold():
            if self._ceiling is not None:
                self._ceiling.admit_new(brief.budget_micro_usd)
            run = BookRun(self._new_id(), brief, plan, Budget(cap=brief.budget_micro_usd))
            self._store_sources(run.run_id, sources)
            if previous_lock is not None and self._artifacts is not None:
                self._artifacts.put(
                    run.run_id,
                    LockShootingScriptStageExecutor.PREVIOUS,
                    previous_lock.encode("utf-8"),
                )
            self._runs.save(run)
        self._queue.enqueue(
            AdvanceRun.KIND, {"run_id": run.run_id, "stage": run.stage, "attempt": 1}
        )
        return run
