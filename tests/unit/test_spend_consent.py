"""Spend consent: a run that would spend past its cap waits for a grant or a denial, and resumes by the rules."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.spend_request import SpendRequest
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.repositories.book_run_codec import BookRunCodec
from engineering_influence.services.advance_run import AdvanceRun
from engineering_influence.services.resolve_spend_consent import ResolveSpendConsent


def run(status: RunStatus = RunStatus.RUNNING, cap: int = 1_000, spent: int = 0) -> BookRun:
    brief = BookBrief(BookKind.NONFICTION, "Windowsill herbs", cap)
    plan = StagePlan(kind=BookKind.NONFICTION, stages=("brief", "outline"))
    return BookRun("run-1", brief, plan, Budget(cap=cap, spent=spent), status=status)


def waiting(requested: int = 700) -> BookRun:
    return run().await_consent(SpendRequest(requested, "brief"))


def test_a_spend_request_needs_a_positive_amount_and_a_stage() -> None:
    with pytest.raises(ValueError):
        SpendRequest(0, "brief")
    with pytest.raises(ValueError):
        SpendRequest(10, "  ")


def test_a_running_run_can_wait_for_consent() -> None:
    stopped = waiting()
    assert stopped.status is RunStatus.AWAITING_CONSENT
    assert stopped.consent == SpendRequest(700, "brief")


def test_a_finished_run_cannot_wait_for_consent() -> None:
    with pytest.raises(ValueError):
        run(RunStatus.COMPLETED).await_consent(SpendRequest(1, "brief"))


def test_a_grant_raises_the_cap_by_exactly_the_request_and_continues() -> None:
    granted = waiting(700).grant()
    assert granted.status is RunStatus.RUNNING
    assert granted.consent is None
    assert granted.budget.cap == 1_700
    assert granted.budget.spent == 0


def test_a_grant_for_a_different_amount_than_asked_is_refused() -> None:
    with pytest.raises(ValueError):
        waiting(700).grant(micro_usd=900)
    assert waiting(700).grant(micro_usd=700).budget.cap == 1_700


def test_a_parked_run_continues_with_the_amount_it_is_granted() -> None:
    parked = run(RunStatus.PARKED_CAPACITY, cap=1_000, spent=400)
    continued = parked.grant(micro_usd=500)
    assert continued.status is RunStatus.RUNNING
    assert continued.budget.cap == 1_500
    assert continued.budget.spent == 400


def test_a_parked_run_needs_an_amount_to_continue_with() -> None:
    with pytest.raises(ValueError):
        run(RunStatus.PARKED_CAPACITY).grant()
    with pytest.raises(ValueError):
        run(RunStatus.PARKED_CAPACITY).grant(micro_usd=0)


def test_a_run_that_is_neither_waiting_nor_parked_cannot_be_granted() -> None:
    with pytest.raises(ValueError):
        run(RunStatus.RUNNING).grant(micro_usd=10)


def test_a_denial_parks_the_run_and_forgets_the_request() -> None:
    parked = waiting().deny()
    assert parked.status is RunStatus.PARKED_CAPACITY
    assert parked.consent is None


def test_only_a_run_waiting_for_consent_can_be_denied() -> None:
    with pytest.raises(ValueError):
        run(RunStatus.PARKED_CAPACITY).deny()


def test_the_codec_keeps_a_pending_request_and_reads_older_documents_without_one() -> None:
    codec = BookRunCodec()
    pending = waiting(700)
    assert codec.decode(codec.encode(pending)) == pending
    older = codec.encode(run())
    assert codec.decode(older).consent is None


class RacedRuns(InMemoryRunRepository):
    """A store where another writer always wins the swap."""

    def swap(self, expected: BookRun, replacement: BookRun) -> bool:
        return False


def stored(status: RunStatus, requested: int = 700) -> InMemoryRunRepository:
    repo = InMemoryRunRepository()
    repo.save(waiting(requested) if status is RunStatus.AWAITING_CONSENT else run(status))
    return repo


def test_a_grant_stores_the_run_running_and_queues_its_stage() -> None:
    repo, queue = stored(RunStatus.AWAITING_CONSENT), InMemoryQueue()
    granted = ResolveSpendConsent(repo, queue).grant("run-1")
    assert granted.status is RunStatus.RUNNING
    assert repo.get("run-1") == granted
    assert queue.jobs == [(AdvanceRun.KIND, {"run_id": "run-1", "stage": "brief", "attempt": 1})]


def test_a_denial_parks_the_run_and_queues_nothing() -> None:
    repo, queue = stored(RunStatus.AWAITING_CONSENT), InMemoryQueue()
    parked = ResolveSpendConsent(repo, queue).deny("run-1")
    assert parked.status is RunStatus.PARKED_CAPACITY
    assert repo.get("run-1") == parked
    assert queue.jobs == []


def test_a_parked_run_is_granted_an_amount_and_queued() -> None:
    repo, queue = stored(RunStatus.PARKED_CAPACITY), InMemoryQueue()
    continued = ResolveSpendConsent(repo, queue).grant("run-1", 300)
    assert continued.budget.cap == 1_300
    assert len(queue.jobs) == 1


def test_an_answer_to_a_run_that_is_not_waiting_is_refused_with_409() -> None:
    with pytest.raises(ApplicationError) as refused:
        ResolveSpendConsent(stored(RunStatus.RUNNING), InMemoryQueue()).grant("run-1")
    assert refused.value.code == "CONSENT_NOT_PENDING"
    assert refused.value.http_status == 409


def test_an_unknown_run_is_refused_with_404() -> None:
    with pytest.raises(ApplicationError) as refused:
        ResolveSpendConsent(InMemoryRunRepository(), InMemoryQueue()).deny("nope")
    assert refused.value.code == "RUN_NOT_FOUND"


def test_an_answer_that_races_another_writer_is_refused_and_queues_nothing() -> None:
    repo = RacedRuns()
    repo.save(waiting())
    queue = InMemoryQueue()
    with pytest.raises(ApplicationError) as refused:
        ResolveSpendConsent(repo, queue).grant("run-1")
    assert refused.value.code == "RUN_CHANGED"
    assert refused.value.retryable
    assert queue.jobs == []


def test_an_advance_message_for_a_run_waiting_for_consent_is_skipped() -> None:
    import asyncio

    from engineering_influence.infrastructure.in_memory_journal import InMemoryJournal
    from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
    from engineering_influence.models.advance_outcome import AdvanceOutcome
    from engineering_influence.services.failure_classifier import FailureClassifier

    class MustNotRun(StageExecutorInterface):
        async def execute(self, run: BookRun, attempt: int) -> object:
            raise AssertionError("a run waiting for consent runs no stage")

    repo = stored(RunStatus.AWAITING_CONSENT)
    advance = AdvanceRun(
        repo,
        InMemoryJournal(),
        MustNotRun(),
        InMemoryQueue(),
        FailureClassifier(),
    )
    outcome = asyncio.run(advance.advance("run-1", "brief", 1))
    assert outcome is AdvanceOutcome.SKIPPED
    stored_run = repo.get("run-1")
    assert stored_run is not None and stored_run.status is RunStatus.AWAITING_CONSENT


def test_a_denial_of_a_run_that_is_not_waiting_is_refused_with_409() -> None:
    with pytest.raises(ApplicationError) as refused:
        ResolveSpendConsent(stored(RunStatus.RUNNING), InMemoryQueue()).deny("run-1")
    assert refused.value.code == "CONSENT_NOT_PENDING"
    assert refused.value.http_status == 409


def test_a_request_the_journal_has_already_overspent_fails_the_run_instead() -> None:
    import asyncio
    from types import SimpleNamespace

    from engineering_influence.errors.spend_consent_needed_error import SpendConsentNeededError
    from engineering_influence.infrastructure.in_memory_journal import InMemoryJournal
    from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
    from engineering_influence.models.advance_outcome import AdvanceOutcome
    from engineering_influence.services.failure_classifier import FailureClassifier

    class Overspent(InMemoryJournal):
        """A journal that already records more spend than the cap."""

        def entries(self, run_id: str) -> list:
            return [SimpleNamespace(cost_micro_usd=2_000)]

    class Refuses(StageExecutorInterface):
        async def execute(self, run: BookRun, attempt: int) -> object:
            raise SpendConsentNeededError(700)

    repo = stored(RunStatus.RUNNING)
    outcome = asyncio.run(
        AdvanceRun(repo, Overspent(), Refuses(), InMemoryQueue(), FailureClassifier()).advance(
            "run-1", "brief", 1
        )
    )
    assert outcome is AdvanceOutcome.FAILED
    failed = repo.get("run-1")
    assert failed is not None and failed.status is RunStatus.FAILED
    assert failed.issues[0].code == "budget-exceeded"
