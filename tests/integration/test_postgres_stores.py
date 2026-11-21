"""The run repository, journal and artifact store under real concurrency on PostgreSQL."""

import hashlib
import os
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

import pytest

from engineering_influence.errors.artifact_conflict_error import ArtifactConflictError
from engineering_influence.infrastructure.schema_migrator import SchemaMigrator
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.journal_entry import JournalEntry
from engineering_influence.models.journal_key import JournalKey
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.repositories.sqlmodel_artifact_store import SqlModelArtifactStore
from engineering_influence.repositories.sqlmodel_journal import SqlModelJournal
from engineering_influence.repositories.sqlmodel_run_repository import SqlModelRunRepository

pytestmark = pytest.mark.integration

WORKERS = 12


@pytest.fixture
def migrated(postgres_url: str) -> str:
    SchemaMigrator().upgrade(postgres_url)
    return postgres_url


def at_the_same_time[T](jobs: list[Callable[[], T]]) -> list[T]:
    """Run every job on its own thread, released together so they genuinely overlap."""
    gate = threading.Barrier(len(jobs))

    def start(job: Callable[[], T]) -> T:
        gate.wait(timeout=30)
        return job()

    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        return [future.result() for future in [pool.submit(start, job) for job in jobs]]


def a_run() -> BookRun:
    brief = BookBrief(
        kind=BookKind.NOVEL, idea="a heist in a lighthouse", budget_micro_usd=5_000_000
    )
    plan = StagePlan(kind=BookKind.NOVEL, stages=("brief", "outline", "draft"))
    return BookRun("run-1", brief, plan, Budget(cap=5_000_000))


def test_a_run_survives_a_round_trip_through_postgresql(migrated: str) -> None:
    repository = SqlModelRunRepository(migrated)
    run = a_run().start().with_issue(QualityIssue("brief", "thin", "short idea"))
    repository.save(run)
    assert repository.get("run-1") == run
    assert repository.run_ids() == ["run-1"]
    repository.close()


def test_when_workers_race_to_change_one_run_exactly_one_wins(migrated: str) -> None:
    repository = SqlModelRunRepository(migrated)
    original = a_run()
    repository.save(original)
    attempts = [
        original.with_issue(QualityIssue("brief", f"worker-{n}", "tried to change it"))
        for n in range(WORKERS)
    ]

    results = at_the_same_time(
        [lambda change=change: repository.swap(original, change) for change in attempts]
    )

    assert results.count(True) == 1
    stored = repository.get("run-1")
    assert stored == attempts[results.index(True)]
    repository.close()


def test_when_workers_record_one_request_they_all_get_the_first_answer(migrated: str) -> None:
    journal = SqlModelJournal(migrated)
    key = JournalKey("m-1", "p", "v1", "c1")

    def record(n: int) -> JournalEntry:
        entry = JournalEntry("run-1", "draft", 1, key, f"answer {n}", 100)
        return journal.record(entry)

    answers = at_the_same_time([lambda n=n: record(n) for n in range(WORKERS)])

    assert len({answer.response for answer in answers}) == 1
    assert [entry.response for entry in journal.entries("run-1")] == [answers[0].response]
    journal.close()


def test_artifacts_come_back_byte_for_byte_including_large_binary_files(migrated: str) -> None:
    store = SqlModelArtifactStore(migrated)
    everything = bytes(range(256))
    large = os.urandom(2 * 1024 * 1024)
    assert store.put("run-1", "all-bytes.bin", everything) == hashlib.sha256(everything).hexdigest()
    store.put("run-1", "book.epub", large)
    assert store.get("run-1", "all-bytes.bin") == everything
    assert store.get("run-1", "book.epub") == large
    assert store.names("run-1") == ["all-bytes.bin", "book.epub"]
    store.close()


def test_workers_storing_the_same_bytes_all_succeed(migrated: str) -> None:
    store = SqlModelArtifactStore(migrated)
    digests = at_the_same_time(
        [lambda: store.put("run-1", "a.md", b"same") for _ in range(WORKERS)]
    )
    assert set(digests) == {hashlib.sha256(b"same").hexdigest()}
    assert store.names("run-1") == ["a.md"]
    store.close()


def test_workers_storing_different_bytes_under_one_name_leave_exactly_one_winner(
    migrated: str,
) -> None:
    store = SqlModelArtifactStore(migrated)

    def attempt(n: int) -> bool:
        try:
            store.put("run-1", "a.md", f"version {n}".encode())
        except ArtifactConflictError:
            return False
        return True

    results = at_the_same_time([lambda n=n: attempt(n) for n in range(WORKERS)])

    assert results.count(True) == 1
    winner = f"version {results.index(True)}".encode()
    assert store.get("run-1", "a.md") == winner
    store.close()
