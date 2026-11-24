# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Wires an evaluation: the stack's own pipeline makes the books and a separately configured model judges them."""

from collections.abc import Callable, Mapping
from datetime import date
from pathlib import Path

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.evaluation.toml_evaluation_files import (
    TomlEvaluationFiles,
)
from engineering_influence.infrastructure.prompt_library.toml_prompt_library import (
    TomlPromptLibrary,
)
from engineering_influence.interfaces.evaluation_files_interface import EvaluationFilesInterface
from engineering_influence.interfaces.manuscript_builder_interface import ManuscriptBuilderInterface
from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.interfaces.release_evaluator_interface import ReleaseEvaluatorInterface
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.models.budget import Budget
from engineering_influence.models.evaluation_case import EvaluationCase
from engineering_influence.models.evaluation_report import EvaluationReport
from engineering_influence.models.evaluation_verdict import EvaluationVerdict
from engineering_influence.models.rubric import Rubric
from engineering_influence.runtime.local_book_maker import LocalBookMaker
from engineering_influence.runtime.stage_executor_runtime import StageExecutorRuntime
from engineering_influence.services.book_judge import BookJudge
from engineering_influence.services.evaluation_reporter import EvaluationReporter
from engineering_influence.services.evaluation_runner import EvaluationRunner
from engineering_influence.services.release_gate import ReleaseGate
from engineering_influence.services.score_parser import ScoreParser
from engineering_influence.services.spend_guard import SpendGuard


class EvaluationRuntime(ReleaseEvaluatorInterface):
    """The writing model is the one the environment names for the stack; the judge is ``EI_EVAL_JUDGE_PROFILE``.

    They are separate on purpose: a model that grades its own writing is the least informative judge, and the judge
    is pinned so that a release's scores and the previous release's are the same measurement. The judge has a budget
    of its own, which it cannot pass.
    """

    JUDGE_PROFILE = "EI_EVAL_JUDGE_PROFILE"

    def __init__(
        self,
        environment: Mapping[str, str],
        secrets: SecretProviderInterface,
        work_dir: Path,
        rubric_path: Path,
        set_path: Path,
        baseline_path: Path | None,
        today: date,
        builder: ManuscriptBuilderInterface | None = None,
        judge: ModelInterface | None = None,
        files: EvaluationFilesInterface | None = None,
    ) -> None:
        self._environment = environment
        self._secrets = secrets
        self._work = work_dir
        self._rubric_path = rubric_path
        self._set_path = set_path
        self._baseline_path = baseline_path
        self._today = today
        self._builder = builder
        self._judge = judge
        self._files = files or TomlEvaluationFiles()

    def evaluate(
        self,
        release: str,
        budget_micro_usd: int,
        judge_budget_micro_usd: int,
        progress: Callable[[str], None],
    ) -> tuple[bytes, EvaluationVerdict]:
        """The evaluation report as bytes, and the verdict on it."""
        rubric = self._files.rubric(self._rubric_path)
        cases = self._files.cases(self._set_path)
        baseline = (
            None if self._baseline_path is None else self._files.baseline(self._baseline_path)
        )
        if self._judge is not None:
            report = self._made_and_judged(
                self._judge,
                rubric,
                cases,
                release,
                budget_micro_usd,
                judge_budget_micro_usd,
                progress,
            )
        else:
            judging = self._judging_runtime()
            try:
                report = self._made_and_judged(
                    judging.model(),
                    rubric,
                    cases,
                    release,
                    budget_micro_usd,
                    judge_budget_micro_usd,
                    progress,
                )
            finally:
                judging.close()
        verdict = ReleaseGate().verdict(report, rubric, baseline)
        return EvaluationReporter().render(report, verdict, rubric), verdict

    def _judging_runtime(self) -> StageExecutorRuntime:
        return StageExecutorRuntime(self._judge_environment(), self._secrets, self._today)

    def _made_and_judged(
        self,
        model: ModelInterface,
        rubric: Rubric,
        cases: tuple[EvaluationCase, ...],
        release: str,
        budget_micro_usd: int,
        judge_budget_micro_usd: int,
        progress: Callable[[str], None],
    ) -> EvaluationReport:
        judge = BookJudge(
            model,
            TomlPromptLibrary(),
            ScoreParser(),
            rubric,
            SpendGuard(Budget(cap=judge_budget_micro_usd)),
        )
        maker = LocalBookMaker(
            self._work, self._environment, self._secrets, self._today, self._builder
        )
        return EvaluationRunner(maker, judge).run(release, cases, budget_micro_usd, progress)

    def _judge_environment(self) -> dict[str, str]:
        profile = self._environment.get(self.JUDGE_PROFILE, "").strip()
        if not profile:
            raise ApplicationError(
                code="EVALUATION_JUDGE_REQUIRED",
                message=f"name the judge's model profile in {self.JUDGE_PROFILE}; "
                "the model that wrote the books is not the one to grade them",
                http_status=422,
            )
        return {
            **self._environment,
            "EI_STAGE_EXECUTOR": "model",
            "EI_STAGE_MODEL_PROFILE": profile,
        }
