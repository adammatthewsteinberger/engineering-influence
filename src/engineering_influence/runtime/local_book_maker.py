# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Makes each case of the evaluation set with the stack's own pipeline, in this process."""

import json
import tomllib
from collections.abc import Mapping
from datetime import date
from pathlib import Path

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.book_maker_interface import BookMakerInterface
from engineering_influence.interfaces.local_book_creator_interface import (
    LocalBookCreatorInterface,
)
from engineering_influence.interfaces.manuscript_builder_interface import ManuscriptBuilderInterface
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.evaluation_case import EvaluationCase
from engineering_influence.models.made_book import MadeBook
from engineering_influence.models.run_status import RunStatus
from engineering_influence.runtime.local_book_runtime import LocalBookRuntime


class LocalBookMaker(BookMakerInterface):
    """Each case is a run of its own under ``work_dir``: its state in ``<case>.state``, its book exported to ``<case>``.

    It is ``ei book create`` without the command line: the same executors, the same checks before anything is spent
    (so a missing author profile stops the whole evaluation, not one book), the same export. A run that fails or
    stops is described, not raised: the evaluation reports it as a book that did not finish. A failed run's
    partial output is still exported, so what it did write can be read.
    """

    def __init__(
        self,
        work_dir: Path,
        environment: Mapping[str, str],
        secrets: SecretProviderInterface,
        today: date,
        builder: ManuscriptBuilderInterface | None = None,
    ) -> None:
        """Remember the work folder, environment, secrets, date and optional builder each case runs with."""
        self._work = work_dir
        self._environment = environment
        self._secrets = secrets
        self._today = today
        self._builder = builder

    def make(self, case: EvaluationCase, budget_micro_usd: int) -> MadeBook:
        """Run the case to the end of its plan within the budget; a run that does not finish is described, not raised."""
        out = self._work / case.name
        creator = self._creator(case)
        try:
            run = creator.start(case.brief(budget_micro_usd), lambda line: None)
            if run.status in (RunStatus.COMPLETED, RunStatus.FAILED):
                self._export(creator, out)
        finally:
            creator.close()
        return self._described(case, run, out)

    def _creator(self, case: EvaluationCase) -> LocalBookCreatorInterface:
        """The runtime that makes one case; its state folder is the case's own, so no two cases share a run."""
        return LocalBookRuntime(
            self._work / f"{case.name}.state",
            self._environment,
            self._secrets,
            self._today,
            builder=self._builder,
        )

    @staticmethod
    def _export(creator: LocalBookCreatorInterface, out: Path) -> None:
        """Write what the run stored; a run that failed before it stored anything has nothing to write, which is not an error here."""
        try:
            creator.export(out)
        except ApplicationError as error:
            if error.code != "RUN_HAS_NO_ARTIFACTS":
                raise

    def _described(self, case: EvaluationCase, run: BookRun, out: Path) -> MadeBook:
        chapters = tuple(
            path.read_text(encoding="utf-8") for path in sorted((out / "src").glob("chapter_*.md"))
        )
        report = self._quality(out)
        spend = report.get("spend")
        estimated = spend.get("estimated_micro_usd") if isinstance(spend, dict) else None
        finished = (
            run.status is RunStatus.COMPLETED and report.get("status") == "pass" and bool(chapters)
        )
        return MadeBook(
            case=case.name,
            kind=case.kind,
            run_status=run.status.value,
            finished=finished,
            title=self._title(out, case),
            chapters=chapters,
            spent_micro_usd=run.budget.spent,
            estimated_micro_usd=estimated if isinstance(estimated, int) else None,
            issues=tuple(f"{issue.code}: {issue.detail}" for issue in run.issues),
        )

    @staticmethod
    def _quality(out: Path) -> dict[str, object]:
        path = out / "run" / "quality-report.json"
        if not path.is_file():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _title(out: Path, case: EvaluationCase) -> str:
        for path in sorted((out / "books").glob("*.toml")):
            title = tomllib.loads(path.read_text(encoding="utf-8")).get("title")
            if isinstance(title, str) and title.strip():
                return title
        return case.title_hint or case.name
