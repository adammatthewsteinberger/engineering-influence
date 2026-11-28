# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""RevisionReportStageExecutor: the stage writes both reports from the stored drafts, revisions and lock, and refuses a
run whose lock, cards or lock file are wrong."""

import asyncio

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.shooting_lock import ShootingLock
from engineering_influence.models.shooting_lock_entry import ShootingLockEntry
from engineering_influence.services.revision_report_stage_executor import (
    RevisionReportStageExecutor,
)
from engineering_influence.services.revision_report_writer import RevisionReportWriter
from engineering_influence.services.scene_card_list import SceneCardList
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes
from engineering_influence.services.shooting_lock_codec import ShootingLockCodec


def card(number: int) -> str:
    return (
        f"## S{number:02d} · scene {number}\n**What changes:** it changes.\n**Therefore:** next.\n"
        f"**Beat:** Set-Up\n**Storyline:** A\n**Sources:** 001\n"
    )


def run() -> BookRun:
    brief = BookBrief(BookKind.SCREENPLAY, "a film", 5_000_000, title_hint="TEST FILM")
    return BookRun(
        run_id="run-1", brief=brief, plan=ScreenplayRecipes().plan(), budget=Budget(cap=5_000_000)
    )


def stage(store: InMemoryArtifactStore) -> RevisionReportStageExecutor:
    return RevisionReportStageExecutor(
        store, SceneCardList(), ShootingLockCodec(), RevisionReportWriter()
    )


def seeded(card_numbers: tuple[int, ...], lock: bytes | None) -> InMemoryArtifactStore:
    """A run with the cards, each card's draft and revision, and the given lock file. Scene 2 keeps its draft: its
    revision is stored unchanged."""
    store = InMemoryArtifactStore()
    store.put("run-1", "scene_cards.md", "\n".join(card(n) for n in card_numbers).encode("utf-8"))
    for number in card_numbers:
        draft = f"INT. ROOM - DAY\n\nScene {number} plays out in full."
        revised = f"INT. ROOM - DAY\n\nScene {number} plays out, tighter."
        store.put("run-1", f"scenes/{number:03d}.md", draft.encode("utf-8"))
        store.put(
            "run-1",
            f"revised/{number:03d}.md",
            (draft if number == 2 else revised).encode("utf-8"),
        )
    if lock is not None:
        store.put("run-1", "shooting_lock.json", lock)
    return store


def lock_bytes(*numbers: int) -> bytes:
    entries = tuple(ShootingLockEntry(number, str(number), False) for number in numbers)
    return ShootingLockCodec().encode(ShootingLock(entries)).encode("utf-8")


def text(store: InMemoryArtifactStore, name: str) -> str:
    data = store.get("run-1", name)
    assert data is not None
    return data.decode("utf-8")


def refused(store: InMemoryArtifactStore, code: str) -> None:
    with pytest.raises(ApplicationError) as error:
        asyncio.run(stage(store).execute(run(), 1))
    assert error.value.code == code


def test_the_stage_writes_the_log_and_the_mapping_in_script_order() -> None:
    store = seeded((1, 2), lock_bytes(1, 2))
    asyncio.run(stage(store).execute(run(), 1))
    assert "| 1 | S01 | revised | " in text(store, "revision_log.md")
    assert "| 2 | S02 | draft kept | " in text(store, "revision_log.md")
    assert "| 2 | S02 | Set-Up | 001 |" in text(store, "source_mapping.md")


def test_a_lock_with_a_scene_the_cards_do_not_have_is_refused() -> None:
    refused(seeded((1,), lock_bytes(1, 2)), "STAGE_OUTPUT_INVALID")


def test_a_run_without_its_lock_is_refused() -> None:
    refused(seeded((1,), None), "STAGE_INPUT_MISSING")


def test_a_lock_that_cannot_be_read_is_refused() -> None:
    refused(seeded((1,), b"not a lock"), "SHOOTING_LOCK_UNREADABLE")
