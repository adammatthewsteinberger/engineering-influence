# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The free rehearsal of a screenplay run from its sources to its locked shooting script, through the real runtime and the HTTP adapters.

The run is given two made-up sources and a scripted local model. Each stage's answer is shaped to pass its mechanical
check, so a stage that stops advancing means the chain is broken, not the fixture. The run stops after the lock: the
scene passes (structure and dialogue) and the render, canon and video stages are not in this rehearsal.
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

LAST = "lock_script"
BRIEF = BookBrief(
    kind=BookKind.SCREENPLAY,
    idea="A crew hides a failing air supply until the stack cracks",
    budget_micro_usd=5_000_000,
    title_hint="Oxygen",
    target_words=400,
)


def trimmed() -> StagePlan:
    plan = ScreenplayRecipes().plan()
    return StagePlan(BookKind.SCREENPLAY, plan.stages[: plan.stages.index(LAST) + 1])


def rehearse(tmp_path: Path) -> SmokeReport:
    with serve() as server:
        return SmokeRun(
            environment(tmp_path, server.url),
            NoSecrets(),
            BRIEF,
            date(2026, 11, 27),
            plan=trimmed(),
            sources=SOURCES,
        ).run()


def test_the_screenplay_stages_advance_in_order_to_the_locked_script(tmp_path: Path) -> None:
    report = rehearse(tmp_path)

    stages = trimmed().stages
    assert tuple(row.stage for row in report.rows) == stages
    outcomes = [row.outcome for row in report.rows]
    assert outcomes == ["advanced"] * (len(stages) - 1) + ["completed"], outcomes
    assert report.status == "completed", report.issues


def test_each_stage_stores_its_answer_and_the_script_is_locked(tmp_path: Path) -> None:
    report = rehearse(tmp_path)

    assert {"digest/001.md", "digest/002.md"} <= set(report.artifacts)
    for name in ("anchors", "audit", "beats", "scene_cards", "visual_grammar"):
        assert any(name in stored for stored in report.artifacts), name
    assert {f"scenes/{n:03d}.md" for n in range(1, 16)} <= set(report.artifacts)
    assert {f"revised/{n:03d}.md" for n in range(1, 16)} <= set(report.artifacts)
    assert {"screenplay.fountain", "shooting_lock.json", "shooting_script.fountain"} <= set(
        report.artifacts
    )
