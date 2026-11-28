# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The free rehearsal of a screenplay run from its sources through every stage of its plan, through the real runtime and the
HTTP adapters.

The run is given two made-up sources and a scripted local model. Each stage's answer is shaped to pass its mechanical
check, so a stage that stops advancing means the chain is broken, not the fixture. The free rehearsal runs the plan to the
video stage: the drafting, the revision passes, the lock, the revision log, a clean canon check (a command that finds
nothing), and the video stage, which writes a not-generated manifest when no provider is named. The render and EPUB stages
need the TeX toolchain, so they run only in the toolchain job, which installs it.
"""

import shutil
import sys
from datetime import date
from pathlib import Path

import pytest
from smoke_rehearsal import NoSecrets, environment, serve
from smoke_run import SmokeReport, SmokeRun
from smoke_screenplay import SOURCES

from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes

LOCK = ScreenplayRecipes.LOCK_STAGE
RENDER = ScreenplayRecipes.RENDER_STAGE
EPUB = ScreenplayRecipes.EPUB_STAGE
VIDEO = ScreenplayRecipes.VIDEO_STAGE
TOOLS = ("latexmk", "lualatex", "tex4ebook", "epubcheck", "pdftoppm")
BRIEF = BookBrief(
    kind=BookKind.SCREENPLAY,
    idea="A crew hides a failing air supply until the stack cracks",
    budget_micro_usd=5_000_000,
    title_hint="Oxygen",
    target_words=400,
)


def trimmed(stop: str, skip: frozenset[str] = frozenset()) -> StagePlan:
    """The screenplay plan up to and including ``stop``, without the stages in ``skip``."""
    plan = ScreenplayRecipes().plan()
    stages = plan.stages[: plan.stages.index(stop) + 1]
    return StagePlan(BookKind.SCREENPLAY, tuple(stage for stage in stages if stage not in skip))


def rehearse(tmp_path: Path, stop: str, skip: frozenset[str] = frozenset()) -> SmokeReport:
    plan = trimmed(stop, skip)
    # The canon check is a command that exits cleanly in the author's folder, so the stage runs and finds nothing.
    settings = {
        "EI_SCREENPLAY_CANON_CHECK": f"{sys.executable} -c pass",
        "EI_SCREENPLAY_CANON_FOLDER": str(tmp_path),
    }
    with serve() as server:
        return SmokeRun(
            environment(tmp_path, server.url, settings),
            NoSecrets(),
            BRIEF,
            date(2026, 11, 27),
            plan=plan,
            sources=SOURCES,
        ).run()


def test_the_screenplay_stages_advance_in_order_to_the_locked_script(tmp_path: Path) -> None:
    report = rehearse(tmp_path, LOCK)

    stages = trimmed(LOCK).stages
    assert tuple(row.stage for row in report.rows) == stages
    outcomes = [row.outcome for row in report.rows]
    assert outcomes == ["advanced"] * (len(stages) - 1) + ["completed"], outcomes
    assert report.status == "completed", report.issues


def test_each_stage_stores_its_answer_and_the_script_is_locked(tmp_path: Path) -> None:
    report = rehearse(tmp_path, LOCK)

    assert {"digest/001.md", "digest/002.md"} <= set(report.artifacts)
    for name in ("anchors", "audit", "beats", "scene_cards", "visual_grammar"):
        assert any(name in stored for stored in report.artifacts), name
    assert {f"scenes/{n:03d}.md" for n in range(1, 16)} <= set(report.artifacts)
    assert {f"revised/{n:03d}.md" for n in range(1, 16)} <= set(report.artifacts)
    assert {"screenplay.fountain", "shooting_lock.json", "shooting_script.fountain"} <= set(
        report.artifacts
    )


def test_the_run_goes_on_through_the_revision_log_canon_check_and_video_stage(
    tmp_path: Path,
) -> None:
    report = rehearse(tmp_path, VIDEO, skip=frozenset({RENDER, EPUB}))

    stages = trimmed(VIDEO, skip=frozenset({RENDER, EPUB})).stages
    assert tuple(row.stage for row in report.rows) == stages
    assert [row.outcome for row in report.rows][-1] == "completed", report.issues
    assert report.status == "completed", report.issues
    assert "revision_log.md" in report.artifacts
    assert "source_mapping.md" in report.artifacts
    assert any(name.startswith("video/") for name in report.artifacts)


@pytest.mark.toolchain
@pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in TOOLS),
    reason="the TeX toolchain is not installed",
)
def test_the_whole_screenplay_plan_ends_in_a_printed_pdf_and_an_epub(tmp_path: Path) -> None:
    report = rehearse(tmp_path, VIDEO)

    assert report.status == "completed", report.issues
    assert any(name.endswith(".pdf") for name in report.artifacts)
    assert any(name.endswith(".epub") for name in report.artifacts)
