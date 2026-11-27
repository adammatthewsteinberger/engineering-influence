# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The free rehearsal of a screenplay run's architecture stages, through the real runtime and the HTTP adapters.

The run is given two made-up sources and a scripted local model. Each architecture stage's answer is shaped to pass
its mechanical check, so a stage that stops advancing means the chain is broken, not the fixture. The drafting,
revision, assembly, render and video stages are not in this rehearsal; the plan is trimmed after the visual grammar.
"""

from datetime import date
from pathlib import Path

from smoke_rehearsal import NoSecrets, environment, serve
from smoke_run import SmokeReport, SmokeRun
from smoke_screenplay import SOURCES

from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes

ARCHITECTURE_LAST = "visual_grammar"
ARCHITECTURE = (
    "digest_sources",
    "brief",
    "anchors",
    "audit",
    "beats",
    "scene_cards",
    "visual_grammar",
)
BRIEF = BookBrief(
    kind=BookKind.SCREENPLAY,
    idea="A crew hides a failing air supply until the stack cracks",
    budget_micro_usd=5_000_000,
    title_hint="Oxygen",
    target_words=400,
)


def rehearse(tmp_path: Path) -> SmokeReport:
    plan = ScreenplayRecipes().plan()
    trimmed = StagePlan(
        BookKind.SCREENPLAY, plan.stages[: plan.stages.index(ARCHITECTURE_LAST) + 1]
    )
    with serve() as server:
        return SmokeRun(
            environment(tmp_path, server.url),
            NoSecrets(),
            BRIEF,
            date(2026, 11, 27),
            plan=trimmed,
            sources=SOURCES,
        ).run()


def test_the_architecture_stages_of_a_screenplay_advance_in_order(tmp_path: Path) -> None:
    report = rehearse(tmp_path)

    assert tuple(row.stage for row in report.rows) == ARCHITECTURE
    outcomes = [row.outcome for row in report.rows]
    assert outcomes == ["advanced"] * (len(ARCHITECTURE) - 1) + ["completed"], outcomes
    assert report.status == "completed", report.issues


def test_each_architecture_stage_stores_its_answer(tmp_path: Path) -> None:
    report = rehearse(tmp_path)

    assert {"digest/001.md", "digest/002.md"} <= set(report.artifacts)
    for name in ("anchors", "audit", "beats", "scene_cards", "visual_grammar"):
        assert any(name in stored for stored in report.artifacts), name
