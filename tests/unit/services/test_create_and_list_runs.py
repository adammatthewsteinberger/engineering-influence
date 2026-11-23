"""CreateRun and ListRuns: a brief becomes a saved, pending run whose first stage is queued; the list reads them back."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.run_status import RunStatus
from engineering_influence.services.advance_run import AdvanceRun
from engineering_influence.services.create_run import CreateRun
from engineering_influence.services.list_runs import ListRuns
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.novel_recipes import NovelRecipes


class Repo(InMemoryRunRepository):
    """Records each save, and can be made to refuse, so the order of save and enqueue can be checked."""

    def __init__(self, log: list[str]) -> None:
        super().__init__()
        self.log = log

    def save(self, run) -> None:  # type: ignore[no-untyped-def]
        self.log.append("save")
        super().save(run)


class Queue(InMemoryQueue):
    def __init__(self, log: list[str]) -> None:
        super().__init__()
        self.log = log

    def enqueue(self, kind: str, payload: dict[str, object]) -> str:
        self.log.append("enqueue")
        return super().enqueue(kind, payload)


def service(
    log: list[str] | None = None, queue: Queue | None = None, repo: Repo | None = None
) -> tuple[CreateRun, Repo, Queue]:
    log = [] if log is None else log
    repo = repo or Repo(log)
    queue = queue or Queue(log)
    plans = {BookKind.NONFICTION: NonfictionRecipes().plan(), BookKind.NOVEL: NovelRecipes().plan()}
    return CreateRun(repo, queue, plans, new_id=lambda: "run-new"), repo, queue


def brief(kind: BookKind = BookKind.NONFICTION, cap: int = 5_000_000) -> BookBrief:
    return BookBrief(kind, "sourdough at home", cap)


def test_a_brief_becomes_a_pending_run_whose_budget_is_the_brief_cap() -> None:
    create, repo, _ = service()
    run = create.create(brief(cap=7_000_000))
    assert (run.run_id, run.status, run.stage) == ("run-new", RunStatus.PENDING, "brief")
    assert run.budget.cap == 7_000_000 and run.budget.spent == 0
    assert repo.get("run-new") == run


def test_the_plan_is_the_one_for_the_kind_of_book() -> None:
    create, _, _ = service()
    assert create.create(brief()).plan.stages == NonfictionRecipes().plan().stages
    assert create.create(brief(BookKind.NOVEL)).plan.stages == NovelRecipes().plan().stages


def test_the_run_is_saved_before_its_first_stage_is_queued() -> None:
    log: list[str] = []
    create, _, _ = service(log)
    create.create(brief())
    assert log == ["save", "enqueue"]


def test_the_first_stage_is_queued_as_a_run_advance_message() -> None:
    create, _, queue = service()
    create.create(brief())
    assert queue.jobs == [(AdvanceRun.KIND, {"run_id": "run-new", "stage": "brief", "attempt": 1})]


def test_a_kind_with_no_plan_is_refused_and_nothing_is_saved_or_queued() -> None:
    log: list[str] = []
    repo = Repo(log)
    queue = Queue(log)
    create = CreateRun(repo, queue, {BookKind.NONFICTION: NonfictionRecipes().plan()})
    with pytest.raises(ApplicationError) as caught:
        create.create(brief(BookKind.NOVEL))
    assert (caught.value.code, caught.value.http_status) == ("RUN_KIND_UNSUPPORTED", 422)
    assert caught.value.message == "this build cannot start a novel book"
    assert log == []


def test_each_brief_gets_a_fresh_run_id_by_default() -> None:
    queue = Queue([])
    repo = Repo([])
    plans = {BookKind.NONFICTION: NonfictionRecipes().plan()}
    create = CreateRun(repo, queue, plans)
    first, second = create.create(brief()), create.create(brief())
    assert first.run_id != second.run_id and len(first.run_id) == 32


def test_list_runs_reads_every_saved_run_back() -> None:
    create, repo, _ = service()
    create.create(brief())
    listed = ListRuns(repo).runs()
    assert [run.run_id for run in listed] == ["run-new"]
    assert listed[0].status is RunStatus.PENDING


def test_list_runs_is_empty_before_any_run() -> None:
    assert ListRuns(Repo([])).runs() == ()


def test_list_runs_skips_an_id_whose_run_vanished_between_the_two_reads() -> None:
    class Vanishing(Repo):
        def get(self, run_id: str):  # type: ignore[no-untyped-def]
            return None

    repo = Vanishing([])
    repo.save(brief_run())
    assert ListRuns(repo).runs() == ()


def brief_run():  # type: ignore[no-untyped-def]
    from engineering_influence.models.book_run import BookRun
    from engineering_influence.models.budget import Budget

    plan = NonfictionRecipes().plan()
    return BookRun("gone", brief(), plan, Budget(cap=5_000_000))


def test_the_advance_kind_is_the_one_the_worker_reads() -> None:
    assert AdvanceRun.KIND == "run.advance"


def test_listed_runs_come_back_in_the_order_the_repository_lists_them() -> None:
    class Ordered(Repo):
        def run_ids(self) -> list[str]:
            return ["b-run", "a-run"]

    repo = Ordered([])
    from engineering_influence.models.book_run import BookRun
    from engineering_influence.models.budget import Budget

    plan = NonfictionRecipes().plan()
    for name in ("a-run", "b-run"):
        repo.save(BookRun(name, brief(), plan, Budget(cap=5_000_000)))
    assert [run.run_id for run in ListRuns(repo).runs()] == ["b-run", "a-run"]
