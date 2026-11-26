"""One book run driven to the end of its plan in this process, and picked up again from where it stopped."""

import hashlib
from dataclasses import replace

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.models.advance_outcome import AdvanceOutcome
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.source_entry import SourceEntry
from engineering_influence.models.spend_request import SpendRequest
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.services.create_run import CreateRun
from engineering_influence.services.interfaces.advance_run_interface import AdvanceRunInterface
from engineering_influence.services.interfaces.local_book_run_interface import (
    LocalBookRunInterface,
)
from engineering_influence.services.local_book_run import LocalBookRun
from engineering_influence.services.resolve_spend_consent import ResolveSpendConsent
from engineering_influence.services.resume_run import ResumeRun

PLAN = StagePlan(BookKind.NONFICTION, ("brief", "outline", "build"))
BRIEF = BookBrief(BookKind.NONFICTION, "bees", 1_000_000)


class Advancer(AdvanceRunInterface):
    """Moves the run one stage at a time, the way the real service does, unless a script says otherwise."""

    def __init__(self, runs: InMemoryRunRepository) -> None:
        self.runs = runs
        self.calls: list[tuple[str, int]] = []
        self.script: dict[tuple[str, int], AdvanceOutcome] = {}
        self.ask_at: str | None = None
        self.park_at: str | None = None
        self.fail_at: str | None = None
        self.slept: list[float] = []

    async def advance(self, run_id: str, stage: str, attempt: int) -> AdvanceOutcome:
        self.calls.append((stage, attempt))
        run = self.runs.get(run_id)
        assert run is not None and run.stage == stage
        if (stage, attempt) in self.script:
            return self.script[(stage, attempt)]
        run = run.start() if run.status is RunStatus.PENDING else run
        if self.ask_at == stage:
            self.ask_at = None
            self.runs.save(run.await_consent(SpendRequest(250_000, stage)))
            return AdvanceOutcome.AWAITING_CONSENT
        if self.park_at == stage:
            self.park_at = None
            self.runs.save(run.park())
            return AdvanceOutcome.PARKED
        if self.fail_at == stage:
            self.runs.save(run.fail())
            return AdvanceOutcome.FAILED
        done = run.advance()
        self.runs.save(done)
        return (
            AdvanceOutcome.COMPLETED
            if done.status is RunStatus.COMPLETED
            else AdvanceOutcome.ADVANCED
        )


def local() -> tuple[LocalBookRun, Advancer, InMemoryRunRepository, list[str]]:
    runs, queue = InMemoryRunRepository(), InMemoryQueue()
    advancer = Advancer(runs)
    book = LocalBookRun(
        CreateRun(runs, queue, {BookKind.NONFICTION: PLAN}),
        advancer,
        ResumeRun(runs, queue),
        ResolveSpendConsent(runs, queue),
        runs,
        advancer.slept.append,
    )
    return book, advancer, runs, []


def test_it_is_a_local_book_run() -> None:
    assert isinstance(local()[0], LocalBookRunInterface)


def test_a_run_is_driven_through_every_stage_and_each_is_reported() -> None:
    book, advancer, _, heard = local()
    run = book.start(BRIEF, heard.append)
    assert run.status is RunStatus.COMPLETED
    assert heard == ["brief: advanced", "outline: advanced", "build: completed"]
    assert advancer.calls == [("brief", 1), ("outline", 1), ("build", 1)]


def test_a_stage_that_will_be_retried_is_retried_after_a_wait_each_time() -> None:
    book, advancer, _, heard = local()
    advancer.script = {
        ("outline", 1): AdvanceOutcome.RETRYING,
        ("outline", 2): AdvanceOutcome.RETRYING,
    }
    run = book.start(BRIEF, heard.append)
    assert run.status is RunStatus.COMPLETED
    assert [call for call in advancer.calls if call[0] == "outline"] == [
        ("outline", 1),
        ("outline", 2),
        ("outline", 3),
    ]
    assert advancer.slept == [2.0, 10.0]
    assert "outline: attempt 1 did not succeed, trying again" in heard


def test_the_wait_between_attempts_stops_growing_at_the_last_delay() -> None:
    book, advancer, _, heard = local()
    advancer.script = {("outline", n): AdvanceOutcome.RETRYING for n in range(1, 5)}
    book.start(BRIEF, heard.append)
    assert advancer.slept == [2.0, 10.0, 30.0, 30.0]


def test_a_run_the_stage_fails_is_handed_back_failed_and_final() -> None:
    book, advancer, _, heard = local()
    advancer.fail_at = "outline"
    run = book.start(BRIEF, heard.append)
    assert run.status is RunStatus.FAILED and run.stage == "outline"
    assert heard[-1] == "outline: failed"
    assert book.resume(True, heard.append).status is RunStatus.FAILED


def test_a_run_that_asks_for_more_budget_stops_and_is_handed_back_as_it_is() -> None:
    book, advancer, _, heard = local()
    advancer.ask_at = "outline"
    run = book.start(BRIEF, heard.append)
    assert run.status is RunStatus.AWAITING_CONSENT and run.stage == "outline"
    assert run.consent is not None and run.consent.requested_micro_usd == 250_000
    assert heard == ["brief: advanced", "outline: awaiting_consent"]


def test_a_second_run_is_refused_in_the_same_place() -> None:
    book, _, _, _ = local()
    book.start(BRIEF, lambda line: None)
    with pytest.raises(ApplicationError) as error:
        book.start(BRIEF, lambda line: None)
    assert error.value.code == "LOCAL_RUN_EXISTS"


def test_there_is_nothing_to_resume_before_a_run_started() -> None:
    book, _, _, _ = local()
    with pytest.raises(ApplicationError) as error:
        book.resume(False, lambda line: None)
    assert error.value.code == "LOCAL_RUN_MISSING"


def test_two_runs_in_one_place_are_not_resumed_at_random() -> None:
    book, _, runs, _ = local()
    book.start(BRIEF, lambda line: None)
    first = runs.get(runs.run_ids()[0])
    assert first is not None
    runs.save(replace(first, run_id="other"))
    with pytest.raises(ApplicationError) as error:
        book.resume(False, lambda line: None)
    assert error.value.code == "LOCAL_RUN_MISSING"


def test_a_run_that_has_vanished_from_the_store_is_reported_not_assumed() -> None:
    book, _, runs, _ = local()
    book.start(BRIEF, lambda line: None)
    runs.get = lambda run_id: None  # type: ignore[method-assign]
    with pytest.raises(ApplicationError) as error:
        book.resume(False, lambda line: None)
    assert error.value.code == "RUN_NOT_FOUND"


def test_a_stopped_run_is_not_given_money_unless_the_person_says_so() -> None:
    book, advancer, _, heard = local()
    advancer.ask_at = "outline"
    book.start(BRIEF, heard.append)
    run = book.resume(False, heard.append)
    assert run.status is RunStatus.AWAITING_CONSENT and run.budget.cap == 1_000_000
    assert advancer.calls[-1] == ("outline", 1) and len(advancer.calls) == 2


def test_approving_the_spend_grants_exactly_what_was_asked_and_continues() -> None:
    book, advancer, _, heard = local()
    advancer.ask_at = "outline"
    book.start(BRIEF, heard.append)
    run = book.resume(True, heard.append)
    assert run.status is RunStatus.COMPLETED and run.budget.cap == 1_250_000
    assert heard[-2:] == ["outline: advanced", "build: completed"]


def test_a_parked_run_is_resumed_and_driven_on() -> None:
    book, advancer, _, heard = local()
    advancer.park_at = "outline"
    parked = book.start(BRIEF, heard.append)
    assert parked.status is RunStatus.PARKED_CAPACITY
    assert book.resume(False, heard.append).status is RunStatus.COMPLETED


def test_a_finished_run_is_returned_as_it_is() -> None:
    book, advancer, _, heard = local()
    book.start(BRIEF, heard.append)
    calls = len(advancer.calls)
    assert book.resume(True, heard.append).status is RunStatus.COMPLETED
    assert len(advancer.calls) == calls


def test_the_sources_are_kept_in_the_run_that_is_started() -> None:
    runs, queue = InMemoryRunRepository(), InMemoryQueue()
    store = InMemoryArtifactStore()
    advancer = Advancer(runs)
    book = LocalBookRun(
        CreateRun(runs, queue, {BookKind.NONFICTION: PLAN}, artifacts=store),
        advancer,
        ResumeRun(runs, queue),
        ResolveSpendConsent(runs, queue),
        runs,
        advancer.slept.append,
    )
    text = "the bees"
    source = SourceEntry(1, text, hashlib.sha256(text.encode("utf-8")).hexdigest())
    run = book.start(BRIEF, lambda line: None, (source,))
    assert store.names(run.run_id) == ["source/001.md"]
