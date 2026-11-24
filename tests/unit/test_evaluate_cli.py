"""``ei evaluate``: it spends money, so it asks twice, and its exit status is the verdict."""

import argparse
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interactions.cli.evaluate_cli import EvaluateCli
from engineering_influence.interactions.cli.interfaces.evaluate_cli_interface import (
    EvaluateCliInterface,
)
from engineering_influence.interfaces.release_evaluator_interface import (
    ReleaseEvaluatorInterface,
)
from engineering_influence.models.evaluation_verdict import EvaluationVerdict


class Evaluator(ReleaseEvaluatorInterface):
    def __init__(self, outcome: EvaluationVerdict | BaseException) -> None:
        self.outcome = outcome
        self.asked: list[tuple[str, int, int]] = []

    def evaluate(
        self,
        release: str,
        budget_micro_usd: int,
        judge_budget_micro_usd: int,
        progress: Callable[[str], None],
    ) -> tuple[bytes, EvaluationVerdict]:
        self.asked.append((release, budget_micro_usd, judge_budget_micro_usd))
        progress("a: making")
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return b'{"ok": true}\n', self.outcome


class Harness:
    def __init__(
        self,
        outcome: EvaluationVerdict | BaseException,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        self.evaluator = Evaluator(outcome)
        self.built: list[tuple[Path, Path, Path, Path | None, Mapping[str, str]]] = []
        self.cli = EvaluateCli(
            self._factory,
            {"EI_ALLOW_PAID": "1"} if environment is None else environment,
            "9.9.9",
        )

    def _factory(
        self,
        work: Path,
        rubric: Path,
        cases: Path,
        baseline: Path | None,
        settings: Mapping[str, str],
    ) -> ReleaseEvaluatorInterface:
        self.built.append((work, rubric, cases, baseline, settings))
        return self.evaluator

    def run(self, *argv: str) -> int:
        parser = argparse.ArgumentParser()
        self.cli.register(parser.add_subparsers(dest="command"))
        return self.cli.run(parser.parse_args(["evaluate", *argv]))


def test_a_passing_evaluation_writes_the_report_and_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    harness = Harness(EvaluationVerdict(()))
    out = tmp_path / "out"
    status = harness.run("--out", str(out), "--budget-usd", "2.5", "--judge-budget-usd", "1")
    assert isinstance(harness.cli, EvaluateCliInterface)
    assert status == 0
    assert (out / "evaluation.json").read_bytes() == b'{"ok": true}\n'
    assert harness.evaluator.asked == [("9.9.9", 2_500_000, 1_000_000)]
    work, rubric, cases, baseline, settings = harness.built[0]
    assert (work, rubric, cases, baseline, dict(settings)) == (
        out,
        Path("evaluation/rubric.toml"),
        Path("evaluation/set.toml"),
        None,
        {},
    )
    shown = capsys.readouterr()
    assert "a: making" in shown.out and "meets the bar" in shown.out and shown.err == ""


def test_a_failing_evaluation_lists_every_reason_and_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    harness = Harness(EvaluationVerdict(("voice: low", "plot: low")))
    status = harness.run(
        "--out", str(tmp_path / "o"), "--budget-usd", "1", "--judge-budget-usd", "1"
    )
    assert status == 1
    shown = capsys.readouterr()
    assert "fail: voice: low" in shown.err and "fail: plot: low" in shown.err
    assert "does NOT meet the bar" in shown.out
    assert (tmp_path / "o" / "evaluation.json").exists()


def test_the_options_reach_the_evaluator(tmp_path: Path) -> None:
    harness = Harness(EvaluationVerdict(()))
    harness.run(
        "--out", str(tmp_path / "o"), "--budget-usd", "1", "--judge-budget-usd", "1",
        "--profile", "p.toml", "--set", "s.toml", "--rubric", "r.toml",
        "--baseline", "b.json", "--release", "2.0.0",
    )  # fmt: skip
    _work, rubric, cases, baseline, settings = harness.built[0]
    assert (rubric, cases, baseline) == (Path("r.toml"), Path("s.toml"), Path("b.json"))
    assert dict(settings) == {"EI_AUTHOR_PROFILE": "p.toml"}
    assert harness.evaluator.asked[0][0] == "2.0.0"


@pytest.mark.parametrize("environment", [{}, {"EI_ALLOW_PAID": "0"}, {"EI_ALLOW_PAID": "true"}])
def test_it_refuses_to_spend_without_the_paid_switch(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], environment: dict[str, str]
) -> None:
    harness = Harness(EvaluationVerdict(()), environment)
    status = harness.run(
        "--out", str(tmp_path / "o"), "--budget-usd", "1", "--judge-budget-usd", "1"
    )
    assert status == 2 and "EI_ALLOW_PAID=1" in capsys.readouterr().err
    assert harness.built == [] and not (tmp_path / "o").exists()


@pytest.mark.parametrize("amount", ["abc", "0", "-1", "0.0000001", ""])
@pytest.mark.parametrize("which", ["--budget-usd", "--judge-budget-usd"])
def test_a_budget_that_is_not_above_zero_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], which: str, amount: str
) -> None:
    harness = Harness(EvaluationVerdict(()))
    given = {"--budget-usd": "1", "--judge-budget-usd": "1", which: amount}
    status = harness.run(
        "--out", str(tmp_path / "o"), "--budget-usd", given["--budget-usd"],
        "--judge-budget-usd", given["--judge-budget-usd"],
    )  # fmt: skip
    assert status == 2 and which in capsys.readouterr().err
    assert harness.evaluator.asked == []


def test_the_smallest_budget_is_one_micro_dollar(tmp_path: Path) -> None:
    harness = Harness(EvaluationVerdict(()))
    harness.run("--out", str(tmp_path / "o"), "--budget-usd", "0.000001", "--judge-budget-usd", "1")
    assert harness.evaluator.asked == [("9.9.9", 1, 1_000_000)]


def test_it_will_not_write_among_an_earlier_evaluations_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "o"
    out.mkdir()
    (out / "earlier.txt").write_text("x")
    harness = Harness(EvaluationVerdict(()))
    assert harness.run("--out", str(out), "--budget-usd", "1", "--judge-budget-usd", "1") == 2
    assert "not a new or empty folder" in capsys.readouterr().err
    assert harness.evaluator.asked == []
    file_out = tmp_path / "f"
    file_out.write_text("x")
    assert harness.run("--out", str(file_out), "--budget-usd", "1", "--judge-budget-usd", "1") == 2


def test_an_empty_existing_folder_is_fine(tmp_path: Path) -> None:
    out = tmp_path / "o"
    out.mkdir()
    harness = Harness(EvaluationVerdict(()))
    assert harness.run("--out", str(out), "--budget-usd", "1", "--judge-budget-usd", "1") == 0


def test_a_failure_of_the_evaluation_is_reported_not_raised(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    harness = Harness(
        ApplicationError(code="JUDGE_BUDGET_EXHAUSTED", message="out of money", http_status=422)
    )
    status = harness.run(
        "--out", str(tmp_path / "o"), "--budget-usd", "1", "--judge-budget-usd", "1"
    )
    assert status == 2 and "error: out of money" in capsys.readouterr().err
    assert not (tmp_path / "o" / "evaluation.json").exists()


def test_a_missing_extra_is_named(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    harness = Harness(ImportError("no module", name="anthropic"))
    status = harness.run(
        "--out", str(tmp_path / "o"), "--budget-usd", "1", "--judge-budget-usd", "1"
    )
    assert status == 1 and "anthropic is missing" in capsys.readouterr().err
