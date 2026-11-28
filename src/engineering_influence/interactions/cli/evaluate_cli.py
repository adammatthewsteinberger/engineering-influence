# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ``ei evaluate`` command."""

import argparse
import sys
from collections.abc import Callable, Mapping
from decimal import Decimal, InvalidOperation
from pathlib import Path

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interactions.cli.interfaces.evaluate_cli_interface import (
    EvaluateCliInterface,
)
from engineering_influence.interfaces.release_evaluator_interface import ReleaseEvaluatorInterface

EvaluatorFor = Callable[
    [Path, Path, Path, Path | None, Mapping[str, str]], ReleaseEvaluatorInterface
]


class EvaluateCli(EvaluateCliInterface):
    """``ei evaluate --out DIR --budget-usd N --judge-budget-usd N``: the A6 evaluation, run by hand or by the nightly job.

    **It spends real money**, so it refuses to start unless ``EI_ALLOW_PAID=1`` is set, and both budgets are required
    and have no default. It writes ``DIR/evaluation.json`` (scores, reasons, spend, the verdict) beside the books it made.
    Exit status: 0 the release meets the bar, 1 it does not (the failures are printed and are in the report), 2 the
    command could not run.
    """

    MICRO = Decimal(1_000_000)

    def __init__(
        self, evaluator_for: EvaluatorFor, environment: Mapping[str, str], default_release: str
    ) -> None:
        """Remember how to build the evaluator, the environment, and the default release label."""
        self._evaluator_for = evaluator_for
        self._environment = environment
        self._release = default_release

    def register(self, subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
        """Add ``evaluate`` to the command line."""
        evaluate = subparsers.add_parser(
            "evaluate",
            help="make the evaluation set into books, score them against the rubric and compare with the last release",
            description="Makes every book of the set with the stack's own pipeline, has a separately configured judge "
            "score each against the rubric, and checks the release against the bar (ADR 0003, A5 and A6). Spends money.",
        )
        evaluate.add_argument(
            "--out",
            type=Path,
            required=True,
            help="a new or empty folder for the books and the report",
        )
        evaluate.add_argument(
            "--budget-usd", required=True, help="the most each book may spend, in dollars"
        )
        evaluate.add_argument(
            "--judge-budget-usd",
            required=True,
            help="the most the judge may spend in all, in dollars",
        )
        evaluate.add_argument(
            "--profile", type=Path, help="the author's details and pricing (TOML)"
        )
        evaluate.add_argument("--set", dest="cases", type=Path, default=Path("evaluation/set.toml"))
        evaluate.add_argument("--rubric", type=Path, default=Path("evaluation/rubric.toml"))
        evaluate.add_argument(
            "--baseline", type=Path, help="the previous release's evaluation.json"
        )
        evaluate.add_argument(
            "--release", default=self._release, help="what to call this release in the report"
        )

    def run(self, arguments: argparse.Namespace) -> int:
        """Run the evaluation and return the process status."""
        if self._environment.get("EI_ALLOW_PAID") != "1":
            print(
                "error: an evaluation spends real money on a writing model and a judge; "
                "set EI_ALLOW_PAID=1 to say you mean it",
                file=sys.stderr,
            )
            return 2
        try:
            per_book = self._micro("--budget-usd", arguments.budget_usd)
            judging = self._micro("--judge-budget-usd", arguments.judge_budget_usd)
            if arguments.out.exists() and (
                not arguments.out.is_dir() or any(arguments.out.iterdir())
            ):
                raise ApplicationError(
                    code="EVALUATION_OUT_NOT_EMPTY",
                    message=f"{arguments.out} is not a new or empty folder; an evaluation never mixes with an earlier one",
                    http_status=409,
                )
            settings = (
                {} if arguments.profile is None else {"EI_AUTHOR_PROFILE": str(arguments.profile)}
            )
            evaluator = self._evaluator_for(
                arguments.out, arguments.rubric, arguments.cases, arguments.baseline, settings
            )
            arguments.out.mkdir(parents=True, exist_ok=True)
            report, verdict = evaluator.evaluate(
                arguments.release, per_book, judging, lambda line: print(line, flush=True)
            )
            (arguments.out / "evaluation.json").write_bytes(report)
        except ImportError as error:
            print(
                f"error: evaluate needs the runtime and publishing extras ({error.name} is missing)",
                file=sys.stderr,
            )
            return 1
        except ApplicationError as error:
            print(f"error: {error.message}", file=sys.stderr)
            return 2
        for failure in verdict.failures:
            print(f"fail: {failure}", file=sys.stderr)
        print(
            f"release {arguments.release}: {'meets the bar' if verdict.passed() else 'does NOT meet the bar'}; "
            f"report in {arguments.out / 'evaluation.json'}"
        )
        return 0 if verdict.passed() else 1

    def _micro(self, flag: str, value: str) -> int:
        try:
            micro = int((Decimal(value) * self.MICRO).to_integral_value())
        except InvalidOperation as error:
            raise ApplicationError(
                code="EVALUATION_BUDGET_INVALID",
                message=f"{flag} is a number of dollars, not {value!r}",
                http_status=422,
            ) from error
        if micro < 1:
            raise ApplicationError(
                code="EVALUATION_BUDGET_INVALID",
                message=f"{flag} is above zero",
                http_status=422,
            )
        return micro
