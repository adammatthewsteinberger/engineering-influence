# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The whole non-fiction plan, end to end, through the real runtime and HTTP adapter, against a scripted local server.

This is the free rehearsal of the paid smoke test: it proves every stage, the budget, the retry loop, the audit and the
folder the run is written to, without a real model. What it cannot say is whether a real model's answers are any good.
"""

import json
from collections.abc import Mapping
from pathlib import Path

import pytest
from smoke_rehearsal import rehearsal, serve
from smoke_run import DEFAULT_IDEA, RUN_ID, LiveSettings, SmokeReport, SmokeRun

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.manuscript_builder_interface import ManuscriptBuilderInterface
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.manuscript_build import ManuscriptBuild


class RehearsalBuilder(ManuscriptBuilderInterface):
    """The free rehearsal has no TeX toolchain, so the book is not built here: the build stage is given a scripted pass.

    The real build, from a run's own output to a strict-release PDF and EPUB, is the toolchain test
    ``tests/toolchain/test_run_builds_book.py``.
    """

    def build(self, files: Mapping[str, bytes], slug: str) -> ManuscriptBuild:
        return ManuscriptBuild(
            True,
            "pass",
            (),
            (),
            (("pdf", "pass"), ("covers", "pass"), ("epub", "pass")),
            (("publication-report.json", b"{}"),),
            (("listing.md", b"# Listing\n"), (f"{slug}.pdf", b"%PDF-1.7")),
        )


def smoke(tmp_path: Path, url: str, cap: int = 5_000_000) -> SmokeRun:
    return rehearsal(tmp_path, url, cap, RehearsalBuilder())


def novel_run(tmp_path: Path) -> SmokeReport:
    with serve() as server:
        return rehearsal(
            tmp_path, server.url, builder=RehearsalBuilder(), kind=BookKind.NOVEL
        ).run()


def run(
    tmp_path: Path, cap: int = 5_000_000, failures: dict[str, int] | None = None
) -> SmokeReport:
    with serve(failures) as server:
        return smoke(tmp_path, server.url, cap).run()


def test_every_stage_of_the_plan_advances_and_the_run_completes(tmp_path: Path) -> None:
    report = run(tmp_path)
    assert report.completed and report.status == "completed"
    assert [row.stage for row in report.rows] == [
        "brief",
        "positioning",
        "research",
        "outline",
        "metadata",
        "draft",
        "revise_structure",
        "revise_lines",
        "copy_edit",
        "assemble",
        "audit",
        "build",
    ]
    assert [row.outcome for row in report.rows] == ["advanced"] * 11 + ["completed"]
    assert {row.attempts for row in report.rows} == {1}
    assert report.issues == ()


def test_a_novel_runs_from_its_brief_to_a_built_book(tmp_path: Path) -> None:
    report = novel_run(tmp_path)
    assert report.completed and report.status == "completed", report.issues
    assert [row.stage for row in report.rows] == [
        "brief",
        "story_bible",
        "beats",
        "outline",
        "metadata",
        "draft",
        "assemble",
        "audit",
        "build",
    ]
    assert [row.outcome for row in report.rows] == ["advanced"] * 8 + ["completed"]
    files = report.artifacts
    config = files["manuscript/books/the-salt-road.toml"].decode()
    assert 'kind = "novel"' in config and 'trim_size = "5.5x8.5"' in config
    assert files["manuscript/src/chapter_02.md"].startswith(b"# The Inn\n\n")
    assert b"Status: pass" in files["audit.md"] and "quality-report.json" in files
    assert "book/the-salt-road.pdf" in files


def test_spend_is_counted_per_stage_and_stays_under_the_cap(tmp_path: Path) -> None:
    report = run(tmp_path, cap=5_000_000)
    paid = {row.stage: row.spent_micro_usd for row in report.rows}
    assert all(paid[stage] > 0 for stage in ("brief", "outline", "draft", "copy_edit"))
    assert paid["assemble"] == 0 and paid["audit"] == 0 and paid["build"] == 0
    assert sum(paid.values()) == report.spent_micro_usd
    assert 0 < report.spent_micro_usd <= report.cap_micro_usd


def test_the_book_the_run_made_is_in_the_artifacts_and_passes_the_audit(tmp_path: Path) -> None:
    report = run(tmp_path)
    assert "manuscript/books/herbs-indoors.toml" in report.artifacts
    assert report.artifacts["manuscript/src/chapter_02.md"].startswith(b"# Water\n\nHerbs like")
    assert report.artifacts["copy_02.md"].endswith(b"Edited. Edited. Edited.")
    assert b"Status: pass" in report.artifacts["audit.md"]
    config = report.artifacts["manuscript/books/herbs-indoors.toml"].decode()
    assert 'author = "Smoke Author"' in config and 'title = "Herbs Indoors"' in config


def test_a_stage_the_provider_fails_once_is_retried_and_the_run_still_completes(
    tmp_path: Path,
) -> None:
    report = run(tmp_path, failures={"Write the chapter outline": 1})
    assert report.completed
    outline = next(row for row in report.rows if row.stage == "outline")
    assert (outline.attempts, outline.outcome) == (2, "advanced")


def test_a_cap_too_small_for_the_first_call_waits_for_consent_with_nothing_spent(
    tmp_path: Path,
) -> None:
    report = run(tmp_path, cap=1)
    assert not report.completed and report.status == "awaiting_consent"
    # The first stage waits; the stages after it never start and are reported as skipped.
    assert (report.rows[0].stage, report.rows[0].outcome) == ("brief", "awaiting_consent")
    assert all(row.outcome == "skipped" for row in report.rows[1:])
    assert report.spent_micro_usd == 0


def test_the_report_and_every_artifact_are_written_to_a_new_folder(tmp_path: Path) -> None:
    report = run(tmp_path)
    folder = tmp_path / "out"
    report.write(folder)
    summary = json.loads((folder / "smoke-report.json").read_text(encoding="utf-8"))
    assert summary["status"] == "completed" and summary["budget"]["cap_micro_usd"] == 5_000_000
    assert [row["stage"] for row in summary["stages"]][-1] == "build"
    assert summary["budget"]["spent_usd"] == round(report.spent_micro_usd / 1_000_000, 4)
    assert (folder / "manuscript" / "src" / "chapter_01.md").is_file()
    assert (folder / "audit" / "release-readiness.json").is_file()
    assert (folder / "quality-report.json").is_file()
    assert RUN_ID not in "".join(summary["artifacts"])
    with pytest.raises(ApplicationError) as error:
        report.write(folder)
    assert error.value.code == "EXPORT_TARGET_NOT_EMPTY"


LIVE = {
    "EI_SMOKE_PROFILE": "writer",
    "EI_MODEL_PROFILES": "/p.toml",
    "EI_MODEL_CATALOG": "/c.toml",
    "EI_SMOKE_BUDGET_MICRO_USD": "3000000",
    "OTHER": "kept",
}


def test_live_settings_need_a_profile_its_files_and_a_cap_with_no_default(tmp_path: Path) -> None:
    for name in (
        "EI_SMOKE_PROFILE",
        "EI_MODEL_PROFILES",
        "EI_MODEL_CATALOG",
        "EI_SMOKE_BUDGET_MICRO_USD",
    ):
        without = {key: value for key, value in LIVE.items() if key != name}
        with pytest.raises(ValueError, match=f"set {name}"):
            LiveSettings.from_environment(without, tmp_path)
    blank = {**LIVE, "EI_SMOKE_BUDGET_MICRO_USD": "  "}
    with pytest.raises(ValueError, match="EI_SMOKE_BUDGET_MICRO_USD"):
        LiveSettings.from_environment(blank, tmp_path)


@pytest.mark.parametrize("bad", ["0", "-5", "three", "1.5", ""])
def test_the_cap_and_the_target_are_whole_numbers_above_zero(tmp_path: Path, bad: str) -> None:
    if bad:
        with pytest.raises(ValueError, match="whole number above zero"):
            LiveSettings.from_environment({**LIVE, "EI_SMOKE_BUDGET_MICRO_USD": bad}, tmp_path)
    with pytest.raises(ValueError, match="EI_SMOKE_TARGET_WORDS is a whole number"):
        LiveSettings.from_environment({**LIVE, "EI_SMOKE_TARGET_WORDS": bad or "0"}, tmp_path)


def test_live_settings_make_a_capped_brief_run_the_model_and_use_a_made_up_author(
    tmp_path: Path,
) -> None:
    settings = LiveSettings.from_environment(LIVE, tmp_path)
    assert settings.brief.budget_micro_usd == 3_000_000
    assert (settings.brief.idea, settings.brief.target_words) == (DEFAULT_IDEA, 1_200)
    assert settings.environment["EI_STAGE_EXECUTOR"] == "model"
    assert settings.environment["EI_STAGE_MODEL_PROFILE"] == "writer"
    assert settings.environment["OTHER"] == "kept"
    author = Path(settings.environment["EI_AUTHOR_PROFILE"])
    assert author.parent == tmp_path and "Smoke Test Author" in author.read_text(encoding="utf-8")
    assert settings.out == tmp_path / "out"


def test_live_settings_take_an_idea_a_target_and_a_folder_from_the_environment(
    tmp_path: Path,
) -> None:
    named = {
        **LIVE,
        "EI_SMOKE_IDEA": "How to brew tea",
        "EI_SMOKE_TARGET_WORDS": "800",
        "EI_SMOKE_OUT": str(tmp_path / "mine"),
        "EI_AUTHOR_PROFILE": "/a/real/person.toml",
    }
    settings = LiveSettings.from_environment(named, tmp_path / "scratch")
    assert (settings.brief.idea, settings.brief.target_words) == ("How to brew tea", 800)
    assert settings.out == tmp_path / "mine"
    assert settings.environment["EI_AUTHOR_PROFILE"] != "/a/real/person.toml"
