"""``ei book create``: the arguments become a brief, the run is made or continued, and the exit status says how it ended."""

import argparse
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.source_library.filesystem_source_library import (
    FilesystemSourceLibrary,
)
from engineering_influence.interactions.cli.book_cli import BookCli
from engineering_influence.interfaces.keep_awake_interface import KeepAwakeInterface
from engineering_influence.interfaces.local_book_creator_interface import (
    LocalBookCreatorInterface,
)
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.budget_plan import BudgetPlan
from engineering_influence.models.cost_estimate import CostEstimate
from engineering_influence.models.export_summary import ExportSummary
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.source_entry import SourceEntry
from engineering_influence.models.spend_request import SpendRequest
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.services.source_intake import SourceIntake

PLAN = StagePlan(BookKind.NONFICTION, ("brief", "build"))


def run_in(status: RunStatus, **changes: object) -> BookRun:
    brief = BookBrief(BookKind.NONFICTION, "bees", 5_000_000)
    run = BookRun("r", brief, PLAN, Budget(cap=5_000_000, spent=1_234_500), stage="build")
    return replace(run, status=status, **changes)  # type: ignore[arg-type]


class Creator(LocalBookCreatorInterface):
    def __init__(self, outcome: BookRun | Exception, plan: BudgetPlan | None = None) -> None:
        self.outcome = outcome
        self.planned = plan
        self.started: list[BookBrief] = []
        self.sources: list[tuple[SourceEntry, ...]] = []
        self.previous_locks: list[str | None] = []
        self.stops: list[str | None] = []
        self.modes: list[str] = []
        self.resumed: list[bool] = []
        self.exported: list[Path] = []
        self.closed = 0

    def _result(self) -> BookRun:
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome

    def plan(self, brief: BookBrief) -> BudgetPlan | None:
        return self.planned

    def start(
        self,
        brief: BookBrief,
        progress: Callable[[str], None],
        sources: tuple[object, ...] = (),
        previous_lock: str | None = None,
        stop_after: str | None = None,
        mode: str = "book",
    ) -> BookRun:
        self.started.append(brief)
        self.modes.append(mode)
        self.sources.append(sources)
        self.previous_locks.append(previous_lock)
        self.stops.append(stop_after)
        progress("brief: advanced")
        return self._result()

    def resume(self, approve_spend: bool, progress: Callable[[str], None]) -> BookRun:
        self.resumed.append(approve_spend)
        return self._result()

    def export(self, directory: Path) -> ExportSummary:
        self.exported.append(directory)
        return ExportSummary(14, 3)

    def close(self) -> None:
        self.closed += 1


class Awake(KeepAwakeInterface):
    """Counts the holds, so a test can tell whether the run was kept awake."""

    def __init__(self) -> None:
        self.holds = 0

    @contextmanager
    def hold(self) -> Iterator[None]:
        self.holds += 1
        yield


class Harness:
    def __init__(
        self,
        outcome: BookRun | Exception,
        refuse: Exception | None = None,
        plan: BudgetPlan | None = None,
    ) -> None:
        self.creator = Creator(outcome, plan)
        self.awake = Awake()
        self.made: list[tuple[Path, Mapping[str, str]]] = []
        self._refuse = refuse

    def creator_for(self, state: Path, settings: Mapping[str, str]) -> LocalBookCreatorInterface:
        self.made.append((state, dict(settings)))
        if self._refuse is not None:
            raise self._refuse
        return self.creator

    def run(self, *argv: str) -> int:
        cli = BookCli(
            lambda root: None,  # type: ignore[arg-type, return-value]
            self.creator_for,
            self.awake,
            lambda folder: SourceIntake(FilesystemSourceLibrary()).intake(folder),
        )
        parser = argparse.ArgumentParser()
        cli.register(parser.add_subparsers(dest="command", required=True))
        return cli.run(parser.parse_args(["book", "create", *argv]))


def test_the_run_is_held_awake_unless_the_author_turns_that_off(tmp_path: Path) -> None:
    harness = Harness(run_in(RunStatus.COMPLETED))
    assert harness.run("how to keep bees", *create(tmp_path)) == 0
    assert harness.awake.holds == 1
    other = Harness(run_in(RunStatus.COMPLETED))
    assert other.run("how to keep bees", *create(tmp_path), "--no-keep-awake") == 0
    assert other.awake.holds == 0


def create(tmp_path: Path, *extra: str) -> list[str]:
    return ["--kind", "nonfiction", "--budget-usd", "5", "--out", str(tmp_path / "out"), *extra]


def test_a_previous_shooting_lock_file_is_passed_to_the_run_as_text(tmp_path: Path) -> None:
    harness = Harness(run_in(RunStatus.COMPLETED))
    lock = tmp_path / "shooting_lock.json"
    lock.write_text('{"version": 1, "entries": []}', encoding="utf-8")
    assert harness.run("a film", *create(tmp_path, "--previous-lock", str(lock))) == 0
    assert harness.creator.previous_locks == ['{"version": 1, "entries": []}']


def test_the_mode_reaches_the_run(tmp_path: Path) -> None:
    harness = Harness(run_in(RunStatus.COMPLETED))
    assert harness.run("a book", *create(tmp_path, "--mode", "audiobook")) == 0
    assert harness.creator.modes == ["audiobook"]


def test_stop_after_names_the_stage_the_run_ends_at(tmp_path: Path) -> None:
    harness = Harness(run_in(RunStatus.COMPLETED))
    assert harness.run("a film", *create(tmp_path, "--stop-after", "scene_cards")) == 0
    assert harness.creator.stops == ["scene_cards"]


def test_a_finished_book_is_written_and_the_command_succeeds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    harness = Harness(run_in(RunStatus.COMPLETED))
    assert harness.run("how to keep bees", *create(tmp_path, "--profile", "me.toml")) == 0
    brief = harness.creator.started[0]
    assert (brief.kind, brief.idea, brief.budget_micro_usd) == (
        BookKind.NONFICTION,
        "how to keep bees",
        5_000_000,
    )
    assert harness.creator.exported == [tmp_path / "out"] and harness.creator.closed == 1
    state, settings = harness.made[0]
    assert state == tmp_path / "out.state" and settings == {"EI_AUTHOR_PROFILE": "me.toml"}
    out = capsys.readouterr().out
    assert "brief: advanced" in out and "14 files" in out and "spent 1.2345 of 5.00 USD" in out


def test_the_optional_details_reach_the_brief(tmp_path: Path) -> None:
    harness = Harness(run_in(RunStatus.COMPLETED))
    harness.run(
        "bees",
        *create(tmp_path),
        "--title",
        "Bees",
        "--audience",
        "beginners",
        "--target-words",
        "900",
        "--trim-size",
        "5.5x8.5",
        "--strict-release",
        "--state-dir",
        str(tmp_path / "keep"),
    )
    brief = harness.creator.started[0]
    assert (brief.title_hint, brief.audience, brief.target_words, brief.trim_size) == (
        "Bees",
        "beginners",
        900,
        "5.5x8.5",
    )
    assert harness.made == [(tmp_path / "keep", {"EI_BUILD_STRICT_RELEASE": "1"})]


@pytest.mark.parametrize("budget", ["0", "-1", "lots", "0.0000001"])
def test_a_budget_that_is_not_a_positive_amount_of_dollars_is_refused(
    tmp_path: Path, budget: str, capsys: pytest.CaptureFixture[str]
) -> None:
    harness = Harness(run_in(RunStatus.COMPLETED))
    argv = ["bees", "--kind", "novel", "--budget-usd", budget, "--out", str(tmp_path / "out")]
    assert harness.run(*argv) == 2
    assert capsys.readouterr().err.startswith("error: ")
    assert harness.made == []


@pytest.mark.parametrize(
    ("argv", "missing"),
    [
        (["--kind", "novel", "--budget-usd", "5"], "an idea"),
        (["bees", "--budget-usd", "5"], "--kind"),
        (["bees", "--kind", "novel"], "--budget-usd"),
    ],
)
def test_an_idea_a_kind_and_a_budget_are_all_needed_to_start(
    tmp_path: Path, argv: list[str], missing: str, capsys: pytest.CaptureFixture[str]
) -> None:
    harness = Harness(run_in(RunStatus.COMPLETED))
    assert harness.run(*argv, "--out", str(tmp_path / "out")) == 2
    assert f"book create needs {missing}" in capsys.readouterr().err
    assert harness.made == []


def test_a_brief_the_model_refuses_is_reported_not_raised(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    harness = Harness(run_in(RunStatus.COMPLETED))
    assert harness.run("bees", *create(tmp_path, "--target-words", "-4")) == 2
    assert "target words must be positive" in capsys.readouterr().err


def test_a_folder_that_already_holds_a_run_is_not_started_over(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "out.state").mkdir()
    harness = Harness(run_in(RunStatus.COMPLETED))
    assert harness.run("bees", *create(tmp_path)) == 2
    assert "add --resume" in capsys.readouterr().err and harness.made == []


def test_a_run_that_stopped_asking_for_money_waits_for_the_persons_word(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    asking = run_in(RunStatus.AWAITING_CONSENT, consent=SpendRequest(250_000, "build"))
    harness = Harness(asking)
    assert harness.run("bees", *create(tmp_path)) == 3
    err = capsys.readouterr().err
    assert "it asked for 0.2500 USD more" in err and "--resume --approve-spend" in err
    assert "Nothing was written" in err and harness.creator.exported == []
    assert harness.creator.closed == 1


def test_a_parked_run_says_it_needs_more_budget(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    harness = Harness(run_in(RunStatus.PARKED_CAPACITY))
    assert harness.run("bees", *create(tmp_path)) == 3
    assert "it needs more budget" in capsys.readouterr().err


def test_a_failed_run_still_writes_what_it_made_and_names_what_went_wrong(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    issue = QualityIssue("build", "stage-failed", "the book did not build", blocking=True)
    harness = Harness(run_in(RunStatus.FAILED, issues=(issue,)))
    assert harness.run("bees", *create(tmp_path)) == 1
    err = capsys.readouterr().err
    assert "issue: stage-failed: the book did not build" in err
    assert "failed at stage 'build'; what it made is in" in err
    assert harness.creator.exported == [tmp_path / "out"]


def test_resuming_needs_the_state_folder_and_passes_the_approval_on(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    harness = Harness(run_in(RunStatus.COMPLETED))
    assert harness.run("--out", str(tmp_path / "out"), "--resume") == 2
    assert "no run to resume" in capsys.readouterr().err
    (tmp_path / "out.state").mkdir()
    assert harness.run("--out", str(tmp_path / "out"), "--resume", "--approve-spend") == 0
    assert harness.creator.resumed == [True] and harness.creator.started == []


def test_a_book_that_cannot_be_made_is_refused_before_the_run_starts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    refusal = ApplicationError(code="AUTHOR_PROFILE_REQUIRED", message="name an author profile")
    harness = Harness(run_in(RunStatus.COMPLETED), refuse=refusal)
    assert harness.run("bees", *create(tmp_path)) == 2
    assert "name an author profile" in capsys.readouterr().err
    assert harness.creator.started == []


def test_missing_extras_are_named(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    harness = Harness(
        run_in(RunStatus.COMPLETED), refuse=ImportError("no sqlmodel", name="sqlmodel")
    )
    assert harness.run("bees", *create(tmp_path)) == 1
    assert "engineering-influence[runtime,publishing]" in capsys.readouterr().err


def test_an_error_while_the_run_goes_is_one_line_and_the_creator_is_still_closed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    harness = Harness(ApplicationError(code="RUN_X", message="the model was refused"))
    assert harness.run("bees", *create(tmp_path)) == 2
    assert "error: the model was refused" in capsys.readouterr().err
    assert harness.creator.closed == 1


ESTIMATE = CostEstimate(
    (("brief", 1_000_000, True), ("draft", 3_000_000, True), ("copy_edit", 2_000_000, False))
)


def planned(cap: int) -> BudgetPlan:
    return BudgetPlan(cap, ESTIMATE)


def test_the_expected_cost_is_said_before_the_book_is_started(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    harness = Harness(run_in(RunStatus.COMPLETED), plan=planned(7_000_000))
    assert harness.run("bees", *create(tmp_path)) == 0
    out = capsys.readouterr().out
    assert (
        "estimate: about 6.00 USD for the whole book (4.00 before editing), against a budget of 7.00: lean"
        in out
    )
    assert "editing passes that run out of money are skipped; the draft is kept" in out


def test_a_budget_below_what_the_book_needs_is_refused_before_anything_is_spent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    harness = Harness(run_in(RunStatus.COMPLETED), plan=planned(3_000_000))
    assert harness.run("bees", *create(tmp_path, "--budget-usd", "3")) == 2
    captured = capsys.readouterr()
    assert "against a budget of 3.00: short" in captured.out
    assert "Use --budget-usd 9.00 or more, or --ignore-estimate to start anyway" in captured.err
    assert harness.creator.started == [] and harness.creator.closed == 1


def test_a_person_who_knows_better_can_start_a_short_budget_anyway(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    harness = Harness(run_in(RunStatus.COMPLETED), plan=planned(3_000_000))
    assert harness.run("bees", *create(tmp_path), "--ignore-estimate") == 0
    out = capsys.readouterr().out
    assert "short" in out and "the run may stop to ask for more budget" in out
    assert len(harness.creator.started) == 1


@pytest.mark.parametrize(
    ("cap", "grade", "advice"),
    [
        (4_000_000, "tight", "the run may stop to ask for more budget"),
        (5_000_000, "tight", "the run may stop to ask for more budget"),
        (9_000_000, "ample", None),
    ],
)
def test_a_tight_budget_warns_and_an_ample_one_says_nothing_more(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], cap: int, grade: str, advice: str | None
) -> None:
    harness = Harness(run_in(RunStatus.COMPLETED), plan=planned(cap))
    assert harness.run("bees", *create(tmp_path)) == 0
    out = capsys.readouterr().out
    assert f"{grade}\n" in out
    assert (advice in out) if advice else ("may stop" not in out and "skipped" not in out)


def test_with_no_priced_model_there_is_no_estimate_and_nothing_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    harness = Harness(run_in(RunStatus.COMPLETED), plan=None)
    assert harness.run("bees", *create(tmp_path)) == 0
    assert "estimate:" not in capsys.readouterr().out


def test_resuming_makes_no_estimate(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "out.state").mkdir()
    harness = Harness(run_in(RunStatus.COMPLETED), plan=planned(1))
    assert harness.run("--out", str(tmp_path / "out"), "--resume") == 0
    assert "estimate:" not in capsys.readouterr().out


# ------------------------------------------------------------------------------ --out is checked first
def holding_a_file(folder: Path) -> Path:
    folder.mkdir(parents=True)
    (folder / "notes.txt").write_text("mine")
    return folder


def test_an_out_folder_that_holds_something_is_refused_before_anything_is_made(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = holding_a_file(tmp_path / "out")
    harness = Harness(run_in(RunStatus.COMPLETED))

    assert harness.run("bees", *create(tmp_path)) == 2

    assert harness.made == [] and harness.creator.started == []
    assert capsys.readouterr().err == (
        f"error: {out} already exists and is not an empty folder; choose a new or empty --out\n"
    )
    assert (out / "notes.txt").read_text() == "mine"


def test_an_out_that_is_a_file_or_a_link_is_refused_the_same_way(tmp_path: Path) -> None:
    (tmp_path / "out").write_text("a file")
    assert Harness(run_in(RunStatus.COMPLETED)).run("bees", *create(tmp_path)) == 2

    (tmp_path / "out").unlink()
    (tmp_path / "elsewhere").mkdir()
    (tmp_path / "out").symlink_to(tmp_path / "elsewhere")
    harness = Harness(run_in(RunStatus.COMPLETED))
    assert harness.run("bees", *create(tmp_path)) == 2
    assert harness.made == []


def test_an_empty_out_folder_that_already_exists_is_fine(tmp_path: Path) -> None:
    (tmp_path / "out").mkdir()
    harness = Harness(run_in(RunStatus.COMPLETED))

    assert harness.run("bees", *create(tmp_path)) == 0
    assert harness.creator.exported == [tmp_path / "out"]


def test_resuming_into_a_folder_that_holds_an_earlier_export_says_how_to_keep_the_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = holding_a_file(tmp_path / "out")
    state = tmp_path / "out.state"
    state.mkdir()
    harness = Harness(run_in(RunStatus.COMPLETED))

    assert harness.run("--out", str(out), "--resume") == 2

    assert harness.made == [] and harness.creator.resumed == []
    assert capsys.readouterr().err == (
        f"error: {out} already exists and is not an empty folder; the run is safe in {state}: "
        f"continue it into a new folder with --out NEW_FOLDER --state-dir {state} --resume\n"
    )


def test_a_run_can_be_continued_into_a_new_folder_from_its_old_state(tmp_path: Path) -> None:
    holding_a_file(tmp_path / "out")
    state = tmp_path / "out.state"
    state.mkdir()
    harness = Harness(run_in(RunStatus.COMPLETED))

    code = harness.run("--out", str(tmp_path / "new"), "--state-dir", str(state), "--resume")

    assert code == 0
    assert harness.made[0][0] == state and harness.creator.exported == [tmp_path / "new"]


def test_a_run_that_already_exists_is_reported_before_the_out_folder_is(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    holding_a_file(tmp_path / "out")
    (tmp_path / "out.state").mkdir()

    assert Harness(run_in(RunStatus.COMPLETED)).run("bees", *create(tmp_path)) == 2
    assert "already holds a run; add --resume" in capsys.readouterr().err


def test_source_files_in_the_folder_reach_the_run_in_name_order(tmp_path: Path) -> None:
    folder = tmp_path / "source"
    folder.mkdir()
    (folder / "b.md").write_text("second", encoding="utf-8")
    (folder / "a.md").write_text("first", encoding="utf-8")
    harness = Harness(run_in(RunStatus.COMPLETED))
    assert harness.run("bees", *create(tmp_path), "--source", str(folder)) == 0
    assert [entry.text for entry in harness.creator.sources[0]] == ["first", "second"]


def test_a_run_without_a_source_folder_is_given_no_sources(tmp_path: Path) -> None:
    harness = Harness(run_in(RunStatus.COMPLETED))
    assert harness.run("bees", *create(tmp_path)) == 0
    assert harness.creator.sources == [()]


def test_a_source_folder_that_is_missing_is_refused_before_the_run_starts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    harness = Harness(run_in(RunStatus.COMPLETED))
    assert harness.run("bees", *create(tmp_path), "--source", str(tmp_path / "nowhere")) == 2
    assert harness.creator.started == []
    assert capsys.readouterr().err.startswith("error: ")
