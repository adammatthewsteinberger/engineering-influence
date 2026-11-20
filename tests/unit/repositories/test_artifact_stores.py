"""The artifact store: every implementation honours the same contract."""

import hashlib
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.artifact_conflict_error import ArtifactConflictError
from engineering_influence.infrastructure.file_artifact_store import FileArtifactStore
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.security.confined_path_guard import ConfinedPathGuard
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.models.artifact_address import ArtifactAddress
from engineering_influence.repositories.sqlmodel_artifact_store import SqlModelArtifactStore

Factory = Callable[[Path, str], ArtifactStoreInterface]

STORES: dict[str, Factory] = {
    "memory": lambda _, __: InMemoryArtifactStore(),
    "file": lambda tmp, _: FileArtifactStore(tmp / "artifacts", ConfinedPathGuard()),
    "sqlite": lambda _, url: SqlModelArtifactStore(url),
}


@pytest.fixture(params=sorted(STORES))
def store(
    request: pytest.FixtureRequest, tmp_path: Path, database_url: str
) -> Iterator[ArtifactStoreInterface]:
    opened = STORES[request.param](tmp_path, database_url)
    yield opened
    if isinstance(opened, SqlModelArtifactStore):
        opened.close()


def test_an_artifact_that_was_never_stored_is_not_found(store: ArtifactStoreInterface) -> None:
    assert store.get("run-1", "book.epub") is None
    assert store.names("run-1") == []


def test_stored_bytes_come_back_unchanged_and_the_digest_is_sha256(
    store: ArtifactStoreInterface,
) -> None:
    data = bytes(range(256)) + "é".encode()
    assert store.put("run-1", "book.epub", data) == hashlib.sha256(data).hexdigest()
    assert store.get("run-1", "book.epub") == data


def test_the_same_bytes_may_be_stored_again(store: ArtifactStoreInterface) -> None:
    first = store.put("run-1", "a.md", b"text")
    assert store.put("run-1", "a.md", b"text") == first
    assert store.names("run-1") == ["a.md"]


def test_different_bytes_under_a_used_name_are_refused(store: ArtifactStoreInterface) -> None:
    store.put("run-1", "a.md", b"text")
    with pytest.raises(ArtifactConflictError, match="already holds different bytes"):
        store.put("run-1", "a.md", b"other")
    assert store.get("run-1", "a.md") == b"text"


def test_names_may_nest_and_are_listed_sorted(store: ArtifactStoreInterface) -> None:
    for name in ("draft/ch-02.md", "book.epub", "draft/ch-01.md"):
        store.put("run-1", name, b"x")
    assert store.names("run-1") == ["book.epub", "draft/ch-01.md", "draft/ch-02.md"]


def test_runs_do_not_see_each_others_artifacts(store: ArtifactStoreInterface) -> None:
    store.put("run-1", "a.md", b"one")
    store.put("run-2", "a.md", b"two")
    assert (store.get("run-1", "a.md"), store.get("run-2", "a.md")) == (b"one", b"two")
    assert store.names("run-2") == ["a.md"]


def test_a_run_id_that_is_a_prefix_of_another_does_not_leak(store: ArtifactStoreInterface) -> None:
    store.put("run-1", "a.md", b"one")
    store.put("run-10", "b.md", b"ten")
    assert store.names("run-1") == ["a.md"]


@pytest.mark.parametrize(
    ("run_id", "name"),
    [
        ("", "a.md"),
        (" ", "a.md"),
        (".", "a.md"),
        ("..", "a.md"),
        ("a/b", "a.md"),
        ("a\\b", "a.md"),
        ("run-1", ""),
        ("run-1", "/abs.md"),
        ("run-1", "../up.md"),
        ("run-1", "a/../b.md"),
        ("run-1", "a//b.md"),
        ("run-1", "./a.md"),
        ("run-1", "a\\b.md"),
        ("run-1", "a.md.part"),
    ],
)
def test_addresses_that_could_leave_the_run_are_refused(
    store: ArtifactStoreInterface, run_id: str, name: str
) -> None:
    with pytest.raises(ValueError):
        store.put(run_id, name, b"x")
    with pytest.raises(ValueError):
        store.get(run_id, name)


def test_an_address_knows_its_path() -> None:
    assert ArtifactAddress("run-1", "draft/ch-01.md").relative_path() == "run-1/draft/ch-01.md"


def test_the_listing_refuses_a_bad_run_id(store: ArtifactStoreInterface) -> None:
    with pytest.raises(ValueError):
        store.names("a/b")


def test_a_file_store_survives_being_reopened(tmp_path: Path) -> None:
    FileArtifactStore(tmp_path, ConfinedPathGuard()).put("run-1", "a.md", b"text")
    assert FileArtifactStore(tmp_path, ConfinedPathGuard()).get("run-1", "a.md") == b"text"


def test_a_crash_mid_write_leaves_nothing_visible_and_the_retry_succeeds(tmp_path: Path) -> None:
    store = FileArtifactStore(tmp_path, ConfinedPathGuard())
    run_dir = tmp_path / "run-1"
    run_dir.mkdir()
    (run_dir / "a.md.part").write_bytes(b"half")
    assert (store.get("run-1", "a.md"), store.names("run-1")) == (None, [])
    store.put("run-1", "a.md", b"whole")
    assert (store.get("run-1", "a.md"), store.names("run-1")) == (b"whole", ["a.md"])
    assert not (run_dir / "a.md.part").exists()


def test_a_symlink_planted_in_the_store_cannot_lead_a_write_outside_it(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "run-1").symlink_to(outside, target_is_directory=True)
    store = FileArtifactStore(root, ConfinedPathGuard())
    with pytest.raises(ApplicationError) as raised:
        store.put("run-1", "a.md", b"x")
    assert raised.value.code == "PATH_ESCAPE"
    assert list(outside.iterdir()) == []


def test_a_sql_store_survives_reopening_the_database(database_url: str) -> None:
    url = database_url
    first = SqlModelArtifactStore(url)
    first.put("run-1", "a.md", b"text")
    first.close()
    second = SqlModelArtifactStore(url)
    assert second.get("run-1", "a.md") == b"text"
    second.close()


class RacingStore(SqlModelArtifactStore):
    """Looks first and finds nothing, as when another worker stores the name a moment later."""

    def __init__(self, url: str) -> None:
        super().__init__(url)
        self.looks = 0

    def _stored_digest(self, run_id: str, name: str) -> str | None:
        self.looks += 1
        return None if self.looks == 1 else super()._stored_digest(run_id, name)


class BlindStore(SqlModelArtifactStore):
    """Never finds anything, even though the row is there."""

    def _stored_digest(self, run_id: str, name: str) -> str | None:
        return None


def test_two_workers_racing_on_one_name_agree_when_the_bytes_match(database_url: str) -> None:
    url = database_url
    winner = SqlModelArtifactStore(url)
    winner.put("run-1", "a.md", b"text")
    loser = RacingStore(url)
    assert loser.put("run-1", "a.md", b"text") == hashlib.sha256(b"text").hexdigest()
    winner.close()
    loser.close()


def test_two_workers_racing_on_one_name_with_different_bytes_conflict(database_url: str) -> None:
    url = database_url
    winner = SqlModelArtifactStore(url)
    winner.put("run-1", "a.md", b"text")
    loser = RacingStore(url)
    with pytest.raises(ArtifactConflictError):
        loser.put("run-1", "a.md", b"other")
    assert loser.get("run-1", "a.md") == b"text"
    winner.close()
    loser.close()


def test_a_duplicate_whose_original_cannot_be_found_is_an_error(database_url: str) -> None:
    store = BlindStore(database_url)
    store.put("run-1", "a.md", b"text")
    with pytest.raises(RuntimeError, match="cannot find the original"):
        store.put("run-1", "a.md", b"text")
    store.close()
