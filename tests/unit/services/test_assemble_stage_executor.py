# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""AssembleStageExecutor: chapters, listing and author details become a manuscript BookLoader reads in strict mode."""

import asyncio
import tomllib
from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.author_profile import AuthorProfile
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.publishing.release_readiness_report import (
    ReleaseReadinessReport,
)
from engineering_influence.models.stage_report import StageReport
from engineering_influence.models.typesetting.text_policy import TextPolicy
from engineering_influence.repositories.typesetting.book_loader import BookLoader
from engineering_influence.services.assemble_stage_executor import AssembleStageExecutor
from engineering_influence.services.book_config_writer import BookConfigWriter
from engineering_influence.services.chapter_cleaner import ChapterCleaner
from engineering_influence.services.dash_rewriter import DashRewriter
from engineering_influence.services.metadata_parser import MetadataParser
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.outline_parser import OutlineParser
from engineering_influence.services.publishing.category_check import CategoryCheck
from engineering_influence.services.publishing.forbidden_content_check import (
    ForbiddenContentCheck,
)
from engineering_influence.services.publishing.metadata_check import MetadataCheck

EM = chr(0x2014)
OUTLINE = """## Chapter 1: The Hive
Purpose: Show how a colony works.
Beats:
- The queen

## Chapter 2: The Site
Purpose: Pick a place for the hive.
Beats:
- Sun and shade
"""
DESCRIPTION = " ".join(["Bees are easier to keep than most people think."] * 10)
METADATA = (
    "Title: Hive Mind\nSubtitle: A calm guide to keeping bees\nDescription:\n"
    + DESCRIPTION
    + "\nKeywords:\n"
    + "".join(f"- keyword {n}\n" for n in range(7))
    + "Categories:\n- Books > Science & Math > Biology\n- Books > Crafts > Bees\n"
)
CHAPTERS = {
    "chapter_01.md": f"Chapter 1: The Hive\n\nA colony {EM} tens of thousands of bees {EM} works as one.",
    "chapter_02.md": "## Chapter 2: The Site\n\nPut it in the sun.\n\n# Shade\n\nBut not all day.",
}
PROFILE = AuthorProfile(
    author="Ann Author",
    publisher="Pub House",
    edition="First Edition",
    author_bio="Ann writes.",
    year=2031,
)


def brief(**changes: Any) -> BookBrief:
    fields: dict[str, Any] = {"idea": "How to keep bees", **changes}
    return BookBrief(kind=BookKind.NONFICTION, budget_micro_usd=1_000_000, **fields)


class World:
    def __init__(
        self,
        *,
        stored: dict[str, str] | None = None,
        profile: AuthorProfile | None = None,
        **brief_changes: Any,
    ) -> None:
        self.store = InMemoryArtifactStore()
        dashes = DashRewriter()
        self.executor = AssembleStageExecutor(
            self.store,
            OutlineParser(),
            MetadataParser(dashes),
            ChapterCleaner(dashes),
            BookConfigWriter(),
            profile,
        )
        self.run = BookRun(
            run_id="run-1",
            brief=brief(**brief_changes),
            plan=NonfictionRecipes().plan(),
            budget=Budget(cap=1_000_000),
            stage="assemble",
        )
        files = {"outline.md": OUTLINE, "metadata.md": METADATA, **CHAPTERS}
        for name, text in (files if stored is None else stored).items():
            self.store.put("run-1", name, text.encode("utf-8"))

    def execute(self) -> StageReport:
        return asyncio.run(self.executor.execute(self.run, 1))

    def refused(self) -> ApplicationError:
        with pytest.raises(ApplicationError) as error:
            self.execute()
        return error.value

    def text(self, name: str) -> str:
        data = self.store.get("run-1", name)
        assert data is not None
        return data.decode("utf-8")

    def written(self) -> list[str]:
        return [name for name in self.store.names("run-1") if name.startswith("manuscript/")]

    def config(self) -> dict[str, Any]:
        return tomllib.loads(self.text(self.written()[0]))

    def materialise(self, root: Path) -> None:
        for name in self.written():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(self.store.get("run-1", name) or b"")


def test_it_is_a_stage_executor() -> None:
    assert isinstance(World().executor, StageExecutorInterface)
    assert AssembleStageExecutor.STAGE == "assemble"


def test_the_chapters_and_the_config_are_written_under_manuscript_with_a_listing() -> None:
    world = World()
    assert world.execute() == StageReport()
    assert world.written() == [
        "manuscript/books/hive-mind.toml",
        "manuscript/src/chapter_01.md",
        "manuscript/src/chapter_02.md",
    ]
    assert world.text("assemble.md") == (
        "# Manuscript\n\n"
        "- manuscript/src/chapter_01.md\n"
        "- manuscript/src/chapter_02.md\n"
        "- manuscript/books/hive-mind.toml\n"
    )


def test_each_chapter_is_cleaned_and_headed_with_the_outlines_title() -> None:
    world = World()
    world.execute()
    assert world.text("manuscript/src/chapter_01.md") == (
        "# The Hive\n\nA colony, tens of thousands of bees, works as one.\n"
    )
    assert world.text("manuscript/src/chapter_02.md") == (
        "# The Site\n\nPut it in the sun.\n\n## Shade\n\nBut not all day.\n"
    )


def test_the_config_carries_the_listing_from_the_metadata_stage() -> None:
    world = World()
    world.execute()
    config = world.config()
    assert (config["kind"], config["title"], config["subtitle"]) == (
        "nonfiction",
        "Hive Mind",
        "A calm guide to keeping bees",
    )
    assert config["description"] == DESCRIPTION
    assert config["release"] == {
        "keywords": [f"keyword {n}" for n in range(7)],
        "categories": ["Books > Science & Math > Biology", "Books > Crafts > Bees"],
    }
    assert "trim_size" not in config and "author" not in config


def test_the_author_profile_is_written_into_the_config_when_there_is_one() -> None:
    world = World(profile=PROFILE)
    world.execute()
    config = world.config()
    assert (config["author"], config["publisher"], config["edition"]) == (
        "Ann Author",
        "Pub House",
        "First Edition",
    )
    assert (config["year"], config["author_bio"]) == (2031, "Ann writes.")


def test_a_listing_made_here_passes_the_release_contracts_metadata_and_category_checks() -> None:
    world = World(profile=PROFILE)
    world.execute()
    config = world.config()
    report = ReleaseReadinessReport(1, "hive-mind", "", "hive-mind.toml", None)
    MetadataCheck().run(report, config, config["release"], "error", "hive-mind.toml")
    CategoryCheck().run(report, config["release"], "error", "hive-mind.toml")
    assert [(f.severity, f.code) for f in report.findings] == []


def test_the_slug_is_the_listings_title_as_ascii_letters_digits_and_single_hyphens() -> None:
    for title, slug in (
        ("Caf\u00e9 Society", "cafe-society"),
        ("  --Odd!!  Name--  ".strip(), "odd-name"),
        ("\u4e66", "book"),
        ("A" * 70 + " b", "a" * 60),
        ("a" * 59 + " b", "a" * 59),
    ):
        world = World(
            stored={
                "outline.md": OUTLINE,
                "metadata.md": METADATA.replace("Hive Mind", title),
                **CHAPTERS,
            }
        )
        world.execute()
        assert world.written()[0] == f"manuscript/books/{slug}.toml"


def test_a_trim_size_in_the_brief_goes_into_the_config() -> None:
    world = World(trim_size="5.5x8.5")
    world.execute()
    assert world.config()["trim_size"] == "5.5x8.5"


def test_a_missing_input_names_what_is_missing() -> None:
    error = World(stored={}).refused()
    assert (error.code, error.http_status) == ("STAGE_INPUT_MISSING", 409)
    assert "outline.md, metadata.md" in error.message
    only_chapters = World(stored={"metadata.md": METADATA, **CHAPTERS}).refused()
    assert "outline.md" in only_chapters.message and "metadata.md" not in only_chapters.message
    only_metadata = World(stored={"outline.md": OUTLINE, **CHAPTERS}).refused()
    assert "metadata.md" in only_metadata.message and "outline.md" not in only_metadata.message
    partial = World(
        stored={"outline.md": OUTLINE, "metadata.md": METADATA, "chapter_02.md": "Text."}
    ).refused()
    assert partial.code == "STAGE_INPUT_MISSING"
    assert "chapter_01.md" in partial.message and "chapter_02.md" not in partial.message


def test_an_unreadable_outline_or_listing_stops_the_stage_with_the_parsers_reason() -> None:
    assert (
        World(stored={"outline.md": "no chapters", "metadata.md": METADATA}).refused().code
        == "OUTLINE_INVALID"
    )
    assert (
        World(stored={"outline.md": OUTLINE, "metadata.md": "no listing"}).refused().code
        == "METADATA_INVALID"
    )


def test_a_refused_chapter_leaves_no_half_manuscript_behind() -> None:
    world = World(
        stored={
            "outline.md": OUTLINE,
            "metadata.md": METADATA,
            **CHAPTERS,
            "chapter_02.md": "Fine.\n[TODO]",
        }
    )
    error = world.refused()
    assert error.code == "MANUSCRIPT_TEXT_REFUSED"
    assert error.message.startswith("chapter 2, line 2: ")
    assert world.written() == []
    assert "assemble.md" not in world.store.names("run-1")


def test_assembling_again_writes_the_same_files_and_changes_nothing() -> None:
    world = World(profile=PROFILE)
    world.execute()
    before = {name: world.store.get("run-1", name) for name in world.store.names("run-1")}
    world.execute()
    assert {name: world.store.get("run-1", name) for name in world.store.names("run-1")} == before


def test_the_manuscript_loads_in_strict_mode_with_the_outlines_titles_and_numbers(
    tmp_path: Path,
) -> None:
    world = World(profile=PROFILE)
    world.execute()
    world.materialise(tmp_path)
    book = BookLoader(tmp_path / "manuscript", strict=True).load(
        tmp_path / "manuscript" / "books" / "hive-mind.toml"
    )
    assert book.slug == "hive-mind"
    assert [(c.number, c.title) for _, chapters in book.parts for c in chapters] == [
        (1, "The Hive"),
        (2, "The Site"),
    ]
    assert book.meta["author"] == "Ann Author" and book.front == [] and book.back == []


chapter_text = st.text(
    alphabet=st.characters(codec="utf-8", blacklist_characters="\x00"),
    max_size=400,
)


@settings(max_examples=150, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(texts=st.lists(chapter_text, min_size=1, max_size=3))
def test_whatever_the_model_wrote_is_refused_or_loads_in_strict_mode_and_passes_the_text_rules(
    texts: list[str], tmp_path_factory: pytest.TempPathFactory
) -> None:
    outline = "\n".join(
        f"## Chapter {n}: Title {n}\nPurpose: Do {n}.\nBeats:\n- Beat {n}\n"
        for n in range(1, len(texts) + 1)
    )
    stored = {"outline.md": outline, "metadata.md": METADATA}
    stored.update({f"chapter_{n:02d}.md": text for n, text in enumerate(texts, 1)})
    world = World(stored=stored, profile=PROFILE)
    try:
        world.execute()
    except ApplicationError:
        assert world.written() == []
        return
    root = tmp_path_factory.mktemp("book")
    world.materialise(root)
    config = next(root.glob("manuscript/books/*.toml"))
    book = BookLoader(root / "manuscript", strict=True).load(config)
    assert sum(len(chapters) for _, chapters in book.parts) == len(texts)
    for _, chapters in book.parts:
        for chapter in chapters:
            problems = ForbiddenContentCheck().run(
                [chapter.body], "First Edition", TextPolicy.for_name(None)
            )
            assert [p for p in problems if "edition" not in p] == []
