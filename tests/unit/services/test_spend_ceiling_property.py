"""Whatever happens, the runs together never hold more unspent budget than the operator allowed."""

from hypothesis import given, settings
from hypothesis import strategies as st

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.budget import Budget
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.spend_limits import SpendLimits
from engineering_influence.models.spend_request import SpendRequest
from engineering_influence.services.create_run import CreateRun
from engineering_influence.services.resolve_spend_consent import ResolveSpendConsent
from engineering_influence.services.spend_ceiling import SpendCeiling

AMOUNT = st.integers(min_value=1, max_value=4_000_000)
STEP = st.one_of(
    st.tuples(st.just("create"), AMOUNT),
    st.tuples(st.just("ask"), st.integers(0, 9), AMOUNT),
    st.tuples(st.just("grant"), st.integers(0, 9)),
    st.tuples(st.just("spend"), st.integers(0, 9), AMOUNT),
    st.tuples(st.just("finish"), st.integers(0, 9)),
)


@settings(max_examples=300, deadline=None)
@given(
    steps=st.lists(STEP, max_size=40),
    per_run=st.integers(min_value=1_000_000, max_value=5_000_000),
    extra=st.integers(min_value=0, max_value=8_000_000),
)
def test_no_sequence_of_creates_grants_and_spending_breaks_a_ceiling(
    steps: list[tuple[object, ...]], per_run: int, extra: int
) -> None:
    limits = SpendLimits(per_run=per_run, outstanding=per_run + extra)
    repo, queue = InMemoryRunRepository(), InMemoryQueue()
    ceiling = SpendCeiling(repo, limits)
    creator = CreateRun(repo, queue, ceiling=ceiling)
    resolver = ResolveSpendConsent(repo, queue, ceiling)

    def nth(index: object) -> str | None:
        ids = repo.run_ids()
        return ids[int(str(index)) % len(ids)] if ids else None

    for step in steps:
        action, *arguments = step
        run_id = nth(arguments[0]) if action != "create" else None
        run = repo.get(run_id) if run_id else None
        try:
            if action == "create":
                creator.create(BookBrief(BookKind.NONFICTION, "bees", int(str(arguments[0]))))
            elif run is not None and action == "ask" and run.status is RunStatus.RUNNING:
                repo.save(run.await_consent(SpendRequest(int(str(arguments[1])), run.stage)))
            elif run is not None and action == "grant" and run.status is RunStatus.AWAITING_CONSENT:
                resolver.grant(run.run_id)
            elif run is not None and action == "spend" and run.status is RunStatus.RUNNING:
                spent = min(run.budget.cap, run.budget.spent + int(str(arguments[1])))
                repo.save(run.with_budget(Budget(cap=run.budget.cap, spent=spent)))
            elif run is not None and action == "finish" and run.status is RunStatus.RUNNING:
                repo.save(run.fail())
        except ApplicationError as refusal:
            assert refusal.code in {"BUDGET_ABOVE_LIMIT", "OUTSTANDING_BUDGET_EXCEEDED"}
        assert ceiling.outstanding() <= per_run + extra
        for run_id in repo.run_ids():
            held = repo.get(run_id)
            assert held is not None and held.budget.cap <= per_run
