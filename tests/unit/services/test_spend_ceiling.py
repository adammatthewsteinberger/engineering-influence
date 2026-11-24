"""The spend ceiling: one check for a new run and for a raise, made before anything is saved or queued."""

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.spend_limits import SpendLimits
from engineering_influence.models.spend_request import SpendRequest
from engineering_influence.services.create_run import CreateRun
from engineering_influence.services.interfaces.spend_ceiling_interface import (
    SpendCeilingInterface,
)
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.resolve_spend_consent import ResolveSpendConsent
from engineering_influence.services.spend_ceiling import SpendCeiling

PLAN = NonfictionRecipes().plan()


def run(run_id: str, cap: int, spent: int = 0) -> BookRun:
    brief = BookBrief(BookKind.NONFICTION, "bees", cap)
    return BookRun(run_id, brief, PLAN, Budget(cap=cap, spent=spent)).start()


def repo_with(*runs: BookRun) -> InMemoryRunRepository:
    repo = InMemoryRunRepository()
    for item in runs:
        repo.save(item)
    return repo


def refused(call: object) -> ApplicationError:
    with pytest.raises(ApplicationError) as error:
        call()  # type: ignore[operator]
    assert error.value.http_status == 422
    return error.value


def test_it_is_a_spend_ceiling_and_with_no_limits_it_admits_anything() -> None:
    ceiling = SpendCeiling(repo_with(run("a", 10**12)), SpendLimits())
    assert isinstance(ceiling, SpendCeilingInterface)
    ceiling.admit_new(10**15)
    ceiling.admit_raise(run("a", 5), 10**15)


def test_a_run_may_have_exactly_the_per_run_ceiling_and_not_a_micro_dollar_more() -> None:
    ceiling = SpendCeiling(repo_with(), SpendLimits(per_run=3_000_000))
    ceiling.admit_new(3_000_000)
    error = refused(lambda: ceiling.admit_new(3_000_001))
    assert (
        error.code == "BUDGET_ABOVE_LIMIT"
        and "3000000" in error.message
        and "3000001" in error.message
    )


def test_a_raise_may_bring_a_cap_to_the_per_run_ceiling_and_no_further() -> None:
    ceiling = SpendCeiling(repo_with(), SpendLimits(per_run=3_000_000))
    ceiling.admit_raise(run("a", 2_000_000), 1_000_000)
    error = refused(lambda: ceiling.admit_raise(run("a", 2_000_000), 1_000_001))
    assert error.code == "BUDGET_ABOVE_LIMIT" and "3000001" in error.message


def test_all_runs_together_may_hold_exactly_the_outstanding_ceiling() -> None:
    ceiling = SpendCeiling(
        repo_with(run("a", 4_000_000), run("b", 3_000_000)), SpendLimits(outstanding=10_000_000)
    )
    ceiling.admit_new(3_000_000)
    error = refused(lambda: ceiling.admit_new(3_000_001))
    assert error.code == "OUTSTANDING_BUDGET_EXCEEDED"
    assert "10000000" in error.message and "7000000" in error.message and "3000001" in error.message


def test_a_raise_counts_only_what_it_adds_to_the_outstanding_total() -> None:
    ceiling = SpendCeiling(
        repo_with(run("a", 4_000_000), run("b", 3_000_000)), SpendLimits(outstanding=10_000_000)
    )
    ceiling.admit_raise(run("b", 3_000_000), 3_000_000)
    assert (
        refused(lambda: ceiling.admit_raise(run("b", 3_000_000), 3_000_001)).code
        == "OUTSTANDING_BUDGET_EXCEEDED"
    )


def test_what_a_run_has_spent_is_no_longer_outstanding() -> None:
    repo = repo_with(run("a", 4_000_000, spent=3_500_000))
    ceiling = SpendCeiling(repo, SpendLimits(outstanding=1_000_000))
    assert ceiling.outstanding() == 500_000
    ceiling.admit_new(500_000)
    refused(lambda: ceiling.admit_new(500_001))


def test_a_finished_run_holds_nothing_and_a_waiting_run_still_does() -> None:
    first, second = run("done", 4_000_000), run("failed", 4_000_000)
    waiting = run("waiting", 2_000_000).await_consent(SpendRequest(1_000_000, "outline"))
    parked = run("parked", 1_000_000).park()
    repo = repo_with(first.advance(), second.fail(), waiting, parked, run("cancelled", 9).cancel())
    # a completed run needs its last stage; walk it there so "completed" is a real status
    last = replace(first, stage=PLAN.stages[-1]).advance()
    repo.save(last)
    assert SpendCeiling(repo, SpendLimits()).outstanding() == 3_000_000


def test_a_run_that_has_vanished_from_the_store_holds_nothing() -> None:
    repo = repo_with(run("a", 1_000_000))
    ids = repo.run_ids()
    repo.get = lambda run_id: None  # type: ignore[method-assign]
    assert ids == ["a"] and SpendCeiling(repo, SpendLimits()).outstanding() == 0


def test_a_new_run_over_a_ceiling_is_refused_before_anything_is_saved_or_queued() -> None:
    repo, queue = repo_with(), InMemoryQueue()
    creator = CreateRun(repo, queue, ceiling=SpendCeiling(repo, SpendLimits(per_run=1_000_000)))
    assert creator.create(BookBrief(BookKind.NONFICTION, "bees", 1_000_000)).budget.cap == 1_000_000
    with pytest.raises(ApplicationError) as error:
        creator.create(BookBrief(BookKind.NONFICTION, "wasps", 1_000_001))
    assert error.value.code == "BUDGET_ABOVE_LIMIT"
    assert len(repo.run_ids()) == 1 and len(queue.jobs) == 1


def test_the_outstanding_ceiling_stops_a_client_that_starts_many_runs() -> None:
    repo, queue = repo_with(), InMemoryQueue()
    creator = CreateRun(repo, queue, ceiling=SpendCeiling(repo, SpendLimits(outstanding=2_500_000)))
    brief = BookBrief(BookKind.NONFICTION, "bees", 1_000_000)
    creator.create(brief)
    creator.create(brief)
    with pytest.raises(ApplicationError) as error:
        creator.create(brief)
    assert error.value.code == "OUTSTANDING_BUDGET_EXCEEDED" and len(repo.run_ids()) == 2


def waiting_run(cap: int, asked: int) -> BookRun:
    return run("w", cap).await_consent(SpendRequest(asked, "outline"))


def test_a_grant_that_would_break_a_ceiling_is_refused_and_leaves_the_run_waiting() -> None:
    repo, queue = repo_with(waiting_run(2_000_000, 1_500_000)), InMemoryQueue()
    resolver = ResolveSpendConsent(repo, queue, SpendCeiling(repo, SpendLimits(per_run=3_000_000)))
    with pytest.raises(ApplicationError) as error:
        resolver.grant("w")
    assert error.value.code == "BUDGET_ABOVE_LIMIT"
    stored = repo.get("w")
    assert stored is not None and stored.budget.cap == 2_000_000 and stored.consent is not None
    assert queue.jobs == []


def test_a_grant_that_fits_goes_through_and_a_denial_is_never_held_back() -> None:
    repo, queue = repo_with(waiting_run(2_000_000, 1_000_000)), InMemoryQueue()
    resolver = ResolveSpendConsent(repo, queue, SpendCeiling(repo, SpendLimits(per_run=3_000_000)))
    assert resolver.grant("w").budget.cap == 3_000_000 and len(queue.jobs) == 1
    other = repo_with(waiting_run(2_000_000, 9_000_000))
    refusing = ResolveSpendConsent(
        other, InMemoryQueue(), SpendCeiling(other, SpendLimits(per_run=3_000_000))
    )
    assert refusing.deny("w").status.value == "parked_capacity"


def test_a_parked_run_is_granted_only_what_the_ceiling_allows() -> None:
    repo, queue = repo_with(run("p", 2_000_000).park()), InMemoryQueue()
    resolver = ResolveSpendConsent(
        repo, queue, SpendCeiling(repo, SpendLimits(outstanding=2_500_000))
    )
    with pytest.raises(ApplicationError) as error:
        resolver.grant("p", 600_000)
    assert error.value.code == "OUTSTANDING_BUDGET_EXCEEDED"
    assert resolver.grant("p", 500_000).budget.cap == 2_500_000


class SlowToCount(InMemoryRunRepository):
    """The first callers to count the runs wait for each other, so that if nothing serializes them they all see the same total.

    A caller that is alone (because a lock keeps the others out) waits a second and a half, once, before the barrier gives up.
    """

    def __init__(self, parties: int) -> None:
        super().__init__()
        self._counting = threading.Barrier(parties)
        self._storing = threading.Barrier(parties)

    @staticmethod
    def _wait(barrier: threading.Barrier) -> None:
        try:
            barrier.wait(timeout=1.5)
        except threading.BrokenBarrierError:
            pass

    def run_ids(self) -> list[str]:
        self._wait(self._counting)
        return super().run_ids()

    def swap(self, expected: BookRun, replacement: BookRun) -> bool:
        # Nobody stores until everyone has counted, so a grant that is not serialized with its check shows itself.
        self._wait(self._storing)
        return super().swap(expected, replacement)


def test_many_requests_at_once_cannot_each_pass_against_the_same_total() -> None:
    repo, queue = SlowToCount(20), InMemoryQueue()
    creator = CreateRun(repo, queue, ceiling=SpendCeiling(repo, SpendLimits(outstanding=5_000_000)))
    refusals: list[str] = []

    def start() -> None:
        try:
            creator.create(BookBrief(BookKind.NONFICTION, "bees", 1_000_000))
        except ApplicationError as error:
            refusals.append(error.code)

    threads = [threading.Thread(target=start) for _ in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(repo.run_ids()) == 5 and len(queue.jobs) == 5
    assert refusals == ["OUTSTANDING_BUDGET_EXCEEDED"] * 15


def test_many_grants_at_once_cannot_each_pass_against_the_same_total() -> None:
    waiting = [
        run(f"w{n}", 1_000_000).await_consent(SpendRequest(1_000_000, "outline")) for n in range(10)
    ]
    repo, queue = SlowToCount(10), InMemoryQueue()
    for item in waiting:
        repo.save(item)
    resolver = ResolveSpendConsent(
        repo, queue, SpendCeiling(repo, SpendLimits(outstanding=13_000_000))
    )
    refusals: list[str] = []

    def grant(run_id: str) -> None:
        try:
            resolver.grant(run_id)
        except ApplicationError as error:
            refusals.append(error.code)

    threads = [threading.Thread(target=grant, args=(item.run_id,)) for item in waiting]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    # ten runs hold ten million; three more million fit, so exactly three grants succeed
    assert len(queue.jobs) == 3 and refusals == ["OUTSTANDING_BUDGET_EXCEEDED"] * 7
    assert SpendCeiling(repo, SpendLimits()).outstanding() == 13_000_000


class Recording(SpendCeilingInterface):
    """Notes when the ceiling is entered, checked and left, to be read beside what the repository sees."""

    def __init__(self, events: list[str]) -> None:
        self.events = events

    @contextmanager
    def hold(self) -> Iterator[None]:
        self.events.append("enter")
        try:
            yield
        finally:
            self.events.append("exit")

    def admit_new(self, cap: int) -> None:
        self.events.append("admit_new")

    def admit_raise(self, run: BookRun, extra: int) -> None:
        self.events.append("admit_raise")

    def outstanding(self) -> int:
        return 0


class Noting(InMemoryRunRepository):
    def __init__(self, events: list[str]) -> None:
        super().__init__()
        self.events = events

    def save(self, run: BookRun) -> None:
        self.events.append("save")
        super().save(run)

    def swap(self, expected: BookRun, replacement: BookRun) -> bool:
        self.events.append("swap")
        return super().swap(expected, replacement)


def test_a_new_run_is_checked_and_saved_inside_one_hold() -> None:
    events: list[str] = []
    repo = Noting(events)
    CreateRun(repo, InMemoryQueue(), ceiling=Recording(events)).create(
        BookBrief(BookKind.NONFICTION, "bees", 1_000_000)
    )
    assert events == ["enter", "admit_new", "save", "exit"]


def test_a_grant_is_checked_and_stored_inside_one_hold() -> None:
    events: list[str] = []
    repo = Noting(events)
    repo.save(waiting_run(2_000_000, 1_000_000))
    events.clear()
    ResolveSpendConsent(repo, InMemoryQueue(), Recording(events)).grant("w")
    assert events == ["enter", "admit_raise", "swap", "exit"]
