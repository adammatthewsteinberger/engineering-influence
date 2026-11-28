# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""SourceDigestStageExecutor: each source gets one digest, a stored digest is kept, and a run with no sources is refused."""

import asyncio

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.interfaces.source_digester_interface import SourceDigesterInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes
from engineering_influence.services.source_digest_stage_executor import (
    SourceDigestStageExecutor,
)


class Digester(SourceDigesterInterface):
    def __init__(self) -> None:
        self.sources: list[str] = []

    def digest(self, run: BookRun, source: str) -> str:
        self.sources.append(source)
        return f"digest of {source}"


def run() -> BookRun:
    brief = BookBrief(BookKind.SCREENPLAY, "a film", 5_000_000)
    return BookRun(
        run_id="run-1", brief=brief, plan=ScreenplayRecipes().plan(), budget=Budget(cap=5_000_000)
    )


def text(store: InMemoryArtifactStore, name: str) -> str:
    data = store.get("run-1", name)
    assert data is not None
    return data.decode("utf-8")


def test_each_source_gets_a_digest_under_its_number() -> None:
    store = InMemoryArtifactStore()
    store.put("run-1", "source/002.md", b"second")
    store.put("run-1", "source/001.md", b"first")
    digester = Digester()
    asyncio.run(SourceDigestStageExecutor(store, digester).execute(run(), 1))
    assert text(store, "digest/001.md") == "digest of first"
    assert text(store, "digest/002.md") == "digest of second"
    assert digester.sources == ["first", "second"]


def test_a_stored_digest_is_kept_and_only_the_missing_one_is_made() -> None:
    store = InMemoryArtifactStore()
    store.put("run-1", "source/001.md", b"first")
    store.put("run-1", "source/002.md", b"second")
    store.put("run-1", "digest/001.md", b"kept")
    digester = Digester()
    asyncio.run(SourceDigestStageExecutor(store, digester).execute(run(), 1))
    assert text(store, "digest/001.md") == "kept"
    assert digester.sources == ["second"]


def test_a_run_with_no_sources_is_refused() -> None:
    with pytest.raises(ApplicationError) as error:
        asyncio.run(
            SourceDigestStageExecutor(InMemoryArtifactStore(), Digester()).execute(run(), 1)
        )
    assert error.value.code == "STAGE_INPUT_MISSING"
