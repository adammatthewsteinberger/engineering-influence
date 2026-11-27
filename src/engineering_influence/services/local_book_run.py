# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Drives one book run to the end of its plan in this process, so no queue and no worker are needed."""

import asyncio
import time
from collections.abc import Callable
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.run_repository_interface import RunRepositoryInterface
from engineering_influence.models.advance_outcome import AdvanceOutcome
from engineering_influence.models.bible_card import BibleCard
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.source_entry import SourceEntry
from engineering_influence.services.interfaces.advance_run_interface import AdvanceRunInterface
from engineering_influence.services.interfaces.create_run_interface import CreateRunInterface
from engineering_influence.services.interfaces.local_book_run_interface import (
    LocalBookRunInterface,
)
from engineering_influence.services.interfaces.resolve_spend_consent_interface import (
    ResolveSpendConsentInterface,
)
from engineering_influence.services.interfaces.resume_run_interface import ResumeRunInterface


class LocalBookRun(LocalBookRunInterface):
    """The same stages, retries and budget a worker would run, one after another in the calling process.

    It stops when the run finishes (completed, failed or cancelled), parks, or asks for more budget, and hands the
    run back as it is; it never grants spend on its own. A stage that the run says to retry is retried after a
    wait, as the queue would delay it, and the run itself fails the stage when its attempts are used up (a failed
    run is final, as it is on a worker). Everything it does goes through the stores it is given, so with stores that
    persist, a process that dies loses nothing that was paid for: ``resume`` picks the one run up where it stopped,
    and a model call already journaled is replayed, not paid for twice.
    """

    RETRY_DELAYS: ClassVar[tuple[float, ...]] = (2.0, 10.0, 30.0)
    STOPPED = frozenset(
        {
            RunStatus.COMPLETED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.PARKED_CAPACITY,
            RunStatus.AWAITING_CONSENT,
        }
    )

    def __init__(
        self,
        creator: CreateRunInterface,
        advancer: AdvanceRunInterface,
        resumer: ResumeRunInterface,
        resolver: ResolveSpendConsentInterface,
        runs: RunRepositoryInterface,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._sleep = sleep
        self._creator = creator
        self._advancer = advancer
        self._resumer = resumer
        self._resolver = resolver
        self._runs = runs

    def start(
        self,
        brief: BookBrief,
        progress: Callable[[str], None],
        sources: tuple[SourceEntry, ...] = (),
        previous_lock: str | None = None,
        stop_after: str | None = None,
        mode: str = "book",
        bible: tuple[BibleCard, ...] = (),
        title: str | None = None,
        previous_script: str | None = None,
        revision: int = 1,
    ) -> BookRun:
        """Create the run for the brief, with its source files, and drive it."""
        if self._runs.run_ids():
            raise ApplicationError(
                code="LOCAL_RUN_EXISTS",
                message="this folder already holds a run; resume it, or start in a new folder",
                http_status=409,
            )
        run = self._creator.create(
            brief,
            sources,
            previous_lock,
            stop_after,
            mode,
            bible=bible,
            title=title,
            previous_script=previous_script,
            revision=revision,
        )
        return self._drive(run.run_id, progress)

    def resume(self, approve_spend: bool, progress: Callable[[str], None]) -> BookRun:
        """Pick the one run up: grant the spend it asked for when told to, un-park a parked run, drive it.

        A run that has finished (completed, failed or cancelled) is returned as it is: a failed run is final.
        """
        ids = self._runs.run_ids()
        if len(ids) != 1:
            raise ApplicationError(
                code="LOCAL_RUN_MISSING",
                message="this folder does not hold exactly one run, so there is nothing to resume",
                http_status=404,
            )
        run = self._load(ids[0])
        if run.status is RunStatus.AWAITING_CONSENT:
            if not approve_spend:
                return run
            self._resolver.grant(run.run_id)
        elif run.status is RunStatus.PARKED_CAPACITY:
            self._resumer.resume(run.run_id)
        return self._drive(run.run_id, progress)

    def _drive(self, run_id: str, progress: Callable[[str], None]) -> BookRun:
        while True:
            run = self._load(run_id)
            if run.status in self.STOPPED:
                return run
            stage, attempt = run.stage, 1
            outcome = asyncio.run(self._advancer.advance(run_id, stage, attempt))
            while outcome is AdvanceOutcome.RETRYING:
                progress(f"{stage}: attempt {attempt} did not succeed, trying again")
                self._sleep(self.RETRY_DELAYS[min(attempt, len(self.RETRY_DELAYS)) - 1])
                attempt += 1
                outcome = asyncio.run(self._advancer.advance(run_id, stage, attempt))
            progress(f"{stage}: {outcome.value}")

    def _load(self, run_id: str) -> BookRun:
        run = self._runs.get(run_id)
        if run is None:
            raise ApplicationError(
                code="RUN_NOT_FOUND", message=f"no run {run_id!r}", http_status=404
            )
        return run
