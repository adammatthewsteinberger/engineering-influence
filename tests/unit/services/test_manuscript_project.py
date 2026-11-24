"""The assembled book of a run is read as the files of a project."""

import asyncio

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.services.manuscript_project import ManuscriptProject
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes

RUN = "run-1"


def run_at(stage: str) -> BookRun:
    brief = BookBrief(BookKind.NONFICTION, "Herbs", 1_000)
    return BookRun(RUN, brief, NonfictionRecipes().plan(), Budget(cap=1_000), stage=stage)


def load(store: InMemoryArtifactStore, stage: str = "build") -> tuple[dict[str, bytes], str]:
    return asyncio.run(ManuscriptProject(store).load(run_at(stage)))


def test_the_manuscript_files_are_the_project_and_the_config_names_the_slug() -> None:
    store = InMemoryArtifactStore()
    store.put(RUN, "manuscript/books/herbs.toml", b"title = 'Herbs'")
    store.put(RUN, "manuscript/src/chapter_01.md", b"# One")
    store.put(RUN, "brief.md", b"not part of the project")
    store.put(RUN, "audit.md", b"nor this")
    files, slug = load(store)
    assert slug == "herbs"
    assert files == {"books/herbs.toml": b"title = 'Herbs'", "src/chapter_01.md": b"# One"}


@pytest.mark.parametrize(
    "names",
    [
        [],
        ["manuscript/src/chapter_01.md"],
        ["manuscript/books/a.toml", "manuscript/books/b.toml"],
        ["books/herbs.toml"],
    ],
)
def test_a_run_needs_exactly_one_book_config(names: list[str]) -> None:
    store = InMemoryArtifactStore()
    for name in names:
        store.put(RUN, name, b"x")
    with pytest.raises(ApplicationError) as refused:
        load(store, "audit")
    assert refused.value.code == "STAGE_INPUT_MISSING"
    assert refused.value.http_status == 409
    assert "'audit'" in refused.value.message
