# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Does a stage by asking a model, from the stage's recipe, and keeps the answer."""

import asyncio
from collections.abc import Callable

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.prompt_library_interface import PromptLibraryInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.interfaces.stage_recipes_interface import StageRecipesInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.model_answer import ModelAnswer
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.prompt_template import PromptTemplate
from engineering_influence.models.stage_recipe import StageRecipe
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.interfaces.ask_model_interface import AskModelInterface
from engineering_influence.services.interfaces.spend_guard_interface import SpendGuardInterface


class ModelStageExecutor(StageExecutorInterface):
    """Reads the stage's input artifacts, renders its prompt, asks, and stores the answer once.

    The run's brief and every earlier answer go into the prompt as blanks that the template
    declares untrusted, so each arrives inside an ``<untrusted>`` block: what a model wrote one
    stage ago is text from outside again, and a request that made it into the brief is data.

    An answer that is not complete (cut off at the model's limit, or declined) or that has no
    text **stops the run**: nothing is stored, and the error carries the reason. Building the next
    stage on an empty or half-written artifact would spend money on top of a defect. The calls
    made are still in the journal, so their cost counts and a person who fixes the brief and
    starts again does not pay for them twice.

    A model call is guarded by a spend guard started from the run's budget. The guard belongs to
    this stage in this process; sharing one across workers is a question for the fan-out stages.
    """

    UNSET = "not given"

    def __init__(
        self,
        recipes: StageRecipesInterface,
        prompts: PromptLibraryInterface,
        artifacts: ArtifactStoreInterface,
        ask: AskModelInterface,
        guards: Callable[[Budget], SpendGuardInterface],
    ) -> None:
        self._recipes = recipes
        self._prompts = prompts
        self._artifacts = artifacts
        self._ask = ask
        self._guards = guards

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Ask for the stage's answer and store it, or raise to stop the run."""
        recipe = self._recipe(run.stage)
        stored = await asyncio.to_thread(self._artifacts.names, run.run_id)
        missing = recipe.missing(stored)
        if missing:
            raise ApplicationError(
                code="STAGE_INPUT_MISSING",
                message=f"stage {run.stage!r} needs {', '.join(missing)}, which this run has not stored",
                http_status=409,
            )
        values = self._brief_values(run)
        for blank, artifact in recipe.input_artifacts().items():
            data = await asyncio.to_thread(self._artifacts.get, run.run_id, artifact)
            values[blank] = (data or b"").decode("utf-8")
        template = self._prompts.get(recipe.template)
        request = ModelRequest(
            system=self._render(template, "system", values),
            prompt=self._render(template, "user", values),
            max_output_tokens=recipe.max_output_tokens,
            prompt_version=template.identifier(),
        )
        answer = await asyncio.to_thread(
            self._ask.ask, self._guards(run.budget), run.run_id, run.stage, attempt, request
        )
        if not answer.complete or not answer.text.strip():
            raise ApplicationError(
                code="STAGE_ANSWER_UNUSABLE", message=self._why(answer, run.stage), http_status=502
            )
        await asyncio.to_thread(
            self._artifacts.put, run.run_id, recipe.output_name(), answer.text.encode("utf-8")
        )
        return StageReport()

    def _recipe(self, stage: str) -> StageRecipe:
        try:
            return self._recipes.recipe(stage)
        except ValueError as error:
            raise ApplicationError(
                code="STAGE_HAS_NO_RECIPE", message=str(error), http_status=422
            ) from error

    def _brief_values(self, run: BookRun) -> dict[str, str]:
        brief = run.brief
        return {
            "idea": brief.idea,
            "audience": brief.audience or self.UNSET,
            "title_hint": brief.title_hint or self.UNSET,
            "target_words": str(brief.target_words) if brief.target_words else self.UNSET,
            "language": brief.language,
        }

    @staticmethod
    def _render(template: PromptTemplate, part: str, values: dict[str, str]) -> str:
        text = template.parts.get(part)
        if text is None:
            raise ApplicationError(
                code="STAGE_TEMPLATE_MISMATCH",
                message=f"template {template.name!r} has no {part!r} part",
                http_status=500,
            )
        needed = set(template.BLANK.findall(text))
        unknown = needed - values.keys()
        if unknown:
            raise ApplicationError(
                code="STAGE_TEMPLATE_MISMATCH",
                message=f"template {template.name!r} asks for {sorted(unknown)}, which the stage cannot give",
                http_status=500,
            )
        return template.render(part, {name: values[name] for name in needed})

    @staticmethod
    def _why(answer: ModelAnswer, stage: str) -> str:
        if answer.issues:
            return f"{stage}: " + "; ".join(f"{i.code}: {i.detail}" for i in answer.issues)
        return f"{stage}: the model returned no text"
