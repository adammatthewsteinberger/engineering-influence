"""The run repository and the journal: every implementation honours the same contract."""

from collections.abc import Callable, Iterator

import pytest
from sqlalchemy.exc import IntegrityError

from engineering_influence.infrastructure.in_memory_journal import InMemoryJournal
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.interfaces.journal_interface import JournalInterface
from engineering_influence.interfaces.run_repository_interface import RunRepositoryInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.journal_entry import JournalEntry
from engineering_influence.models.journal_key import JournalKey
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.repositories.book_run_codec import BookRunCodec
from engineering_influence.repositories.sqlmodel_journal import SqlModelJournal
from engineering_influence.repositories.sqlmodel_run_repository import SqlModelRunRepository

RunFactory = Callable[[str], RunRepositoryInterface]
JournalFactory = Callable[[str], JournalInterface]

RUN_REPOSITORIES: dict[str, RunFactory] = {
    "memory": lambda _: InMemoryRunRepository(),
    "sqlite": SqlModelRunRepository,
}
JOURNALS: dict[str, JournalFactory] = {
    "memory": lambda _: InMemoryJournal(),
    "sqlite": SqlModelJournal,
}


def make_run(run_id: str = "run-1") -> BookRun:
    brief = BookBrief(
        kind=BookKind.NOVEL,
        idea="a heist in a lighthouse",
        budget_micro_usd=5_000_000,
        title_hint="Ledger",
        target_words=60_000,
    )
    plan = StagePlan(kind=BookKind.NOVEL, stages=("brief", "outline", "draft"))
    return BookRun(run_id=run_id, brief=brief, plan=plan, budget=Budget(cap=5_000_000))


def make_entry(
    *, run_id: str = "run-1", stage: str = "draft", response: str = "text", context: str = "c1"
) -> JournalEntry:
    key = JournalKey(model="m-1", params_hash="p", prompt_version="v1", context_hash=context)
    return JournalEntry(
        run_id=run_id, stage=stage, attempt=1, key=key, response=response, cost_micro_usd=900
    )


@pytest.fixture(params=sorted(RUN_REPOSITORIES))
def runs(request: pytest.FixtureRequest, database_url: str) -> Iterator[RunRepositoryInterface]:
    repository = RUN_REPOSITORIES[request.param](database_url)
    yield repository
    if isinstance(repository, SqlModelRunRepository):
        repository.close()


@pytest.fixture(params=sorted(JOURNALS))
def journal(request: pytest.FixtureRequest, database_url: str) -> Iterator[JournalInterface]:
    store = JOURNALS[request.param](database_url)
    yield store
    if isinstance(store, SqlModelJournal):
        store.close()


def test_a_run_that_was_never_saved_is_not_found(runs: RunRepositoryInterface) -> None:
    assert runs.get("run-1") is None
    assert runs.run_ids() == []


def test_a_saved_run_comes_back_equal(runs: RunRepositoryInterface) -> None:
    run = make_run().with_issue(QualityIssue(stage="draft", code="thin", detail="400 words"))
    runs.save(run)
    assert runs.get("run-1") == run


def test_saving_again_replaces_the_earlier_state(runs: RunRepositoryInterface) -> None:
    runs.save(make_run())
    moved = make_run().advance().advance().park()
    runs.save(moved)
    stored = runs.get("run-1")
    assert stored == moved
    assert (stored.stage, stored.status.value) == ("draft", "parked_capacity")  # type: ignore[union-attr]
    assert runs.run_ids() == ["run-1"]


def test_a_swap_stores_the_replacement_when_the_run_is_unchanged(
    runs: RunRepositoryInterface,
) -> None:
    runs.save(make_run())
    moved = make_run().advance()
    assert runs.swap(make_run(), moved) is True
    assert runs.get("run-1") == moved


def test_a_swap_changes_nothing_when_another_worker_got_there_first(
    runs: RunRepositoryInterface,
) -> None:
    runs.save(make_run())
    rival = make_run().advance()
    runs.save(rival)
    assert runs.swap(make_run(), make_run().advance().advance()) is False
    assert runs.get("run-1") == rival


def test_a_swap_on_a_run_that_was_never_saved_changes_nothing(runs: RunRepositoryInterface) -> None:
    assert runs.swap(make_run(), make_run().advance()) is False
    assert runs.get("run-1") is None


def test_a_swap_cannot_move_a_run_to_another_id(runs: RunRepositoryInterface) -> None:
    runs.save(make_run())
    with pytest.raises(ValueError, match="cannot change the run id"):
        runs.swap(make_run(), make_run("run-2"))
    assert runs.run_ids() == ["run-1"]


def test_runs_are_listed_in_sorted_order(runs: RunRepositoryInterface) -> None:
    for run_id in ("run-b", "run-a", "run-c"):
        runs.save(make_run(run_id))
    assert runs.run_ids() == ["run-a", "run-b", "run-c"]


def test_a_budget_in_flight_survives_a_save(runs: RunRepositoryInterface) -> None:
    run = make_run().with_budget(Budget(cap=5_000_000).reserve(1_000_000))
    runs.save(run)
    stored = runs.get("run-1")
    assert stored is not None
    assert (stored.budget.reserved, stored.budget.remaining()) == (1_000_000, 4_000_000)


def test_the_codec_text_is_stable_for_equal_runs() -> None:
    codec = BookRunCodec()
    assert codec.encode(make_run()) == codec.encode(make_run())
    assert codec.decode(codec.encode(make_run())) == make_run()


def test_a_sql_run_survives_reopening_the_database(database_url: str) -> None:
    url = database_url
    first = SqlModelRunRepository(url)
    first.save(make_run().advance())
    first.close()
    second = SqlModelRunRepository(url)
    assert second.get("run-1") == make_run().advance()
    second.close()


def test_a_request_that_was_not_made_is_not_found(journal: JournalInterface) -> None:
    assert journal.find("run-1", "draft", make_entry().key.digest()) is None
    assert journal.entries("run-1") == []


def test_a_recorded_answer_is_found_by_its_request(journal: JournalInterface) -> None:
    entry = make_entry()
    assert journal.record(entry) == entry
    assert journal.find("run-1", "draft", entry.key.digest()) == entry


def test_the_first_answer_to_a_request_wins(journal: JournalInterface) -> None:
    first = make_entry(response="first")
    journal.record(first)
    assert journal.record(make_entry(response="second")) == first
    assert [e.response for e in journal.entries("run-1")] == ["first"]


def test_the_same_request_in_another_stage_or_run_is_recorded_separately(
    journal: JournalInterface,
) -> None:
    journal.record(make_entry())
    journal.record(make_entry(stage="outline"))
    journal.record(make_entry(run_id="run-2"))
    assert [e.stage for e in journal.entries("run-1")] == ["draft", "outline"]
    assert len(journal.entries("run-2")) == 1


def test_a_different_context_is_a_different_request(journal: JournalInterface) -> None:
    journal.record(make_entry(context="c1"))
    journal.record(make_entry(context="c2"))
    assert len(journal.entries("run-1")) == 2


def test_journal_entries_keep_the_order_they_were_recorded(journal: JournalInterface) -> None:
    for context in ("c3", "c1", "c2"):
        journal.record(make_entry(context=context))
    assert [e.key.context_hash for e in journal.entries("run-1")] == ["c3", "c1", "c2"]


def test_a_sql_journal_survives_reopening_the_database(database_url: str) -> None:
    url = database_url
    first = SqlModelJournal(url)
    first.record(make_entry())
    first.close()
    second = SqlModelJournal(url)
    assert second.find("run-1", "draft", make_entry().key.digest()) == make_entry()
    second.close()


class RacingJournal(SqlModelJournal):
    """Looks first and finds nothing, as when another worker inserts a moment later."""

    def __init__(self, url: str) -> None:
        super().__init__(url)
        self.looks = 0

    def find(self, run_id: str, stage: str, digest: str) -> JournalEntry | None:
        self.looks += 1
        if self.looks == 1:
            return None
        return super().find(run_id, stage, digest)


class BlindJournal(SqlModelJournal):
    """Never finds anything, even though the row is there."""

    def find(self, run_id: str, stage: str, digest: str) -> JournalEntry | None:
        return None


def test_two_workers_racing_on_one_request_converge_on_the_first_answer(database_url: str) -> None:
    url = database_url
    winner = SqlModelJournal(url)
    winner.record(make_entry(response="winner"))
    loser = RacingJournal(url)
    assert loser.record(make_entry(response="loser")).response == "winner"
    assert [e.response for e in loser.entries("run-1")] == ["winner"]
    winner.close()
    loser.close()


def test_a_duplicate_whose_original_cannot_be_found_is_an_error(database_url: str) -> None:
    url = database_url
    journal = BlindJournal(url)
    journal.record(make_entry())
    with pytest.raises(RuntimeError, match="cannot find the original"):
        journal.record(make_entry(response="again"))
    journal.close()


def test_the_database_itself_refuses_a_duplicate_request(database_url: str) -> None:
    from sqlmodel import Session

    journal = SqlModelJournal(database_url)
    journal.record(make_entry())
    with Session(journal._engine) as session, pytest.raises(IntegrityError):
        session.add(journal._row(make_entry(response="again"), make_entry().key.digest()))
        session.commit()
    journal.close()


def test_an_unpooled_sql_repository_works_and_holds_no_connection_open(database_url: str) -> None:
    repository = SqlModelRunRepository(database_url, pooled=False)
    repository.save(make_run())
    assert repository.get("run-1") == make_run()
    assert repository.swap(make_run(), make_run().advance()) is True
    assert type(repository._engine.pool).__name__ == "NullPool"
