# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Does a stage by asking a model, from the stage's recipe, and keeps the answer."""

import asyncio
from collections.abc import Callable

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.prompt_library_interface import PromptLibraryInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.interfaces.stage_guidance_interface import StageGuidanceInterface
from engineering_influence.interfaces.stage_output_check_interface import (
    StageOutputCheckInterface,
)
from engineering_influence.interfaces.stage_recipes_interface import StageRecipesInterface
from engineering_influence.interfaces.tool_grants_interface import ToolGrantsInterface
from engineering_influence.interfaces.tool_registry_interface import ToolRegistryInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.prompt_template import PromptTemplate
from engineering_influence.models.stage_recipe import StageRecipe
from engineering_influence.models.stage_report import StageReport
from engineering_influence.models.tool_definition import ToolDefinition
from engineering_influence.models.tool_loop_result import ToolLoopResult
from engineering_influence.services.interfaces.run_tool_loop_interface import (
    RunToolLoopInterface,
)
from engineering_influence.services.interfaces.spend_guard_interface import SpendGuardInterface


class ModelStageExecutor(StageExecutorInterface):
    """Reads the stage's input artifacts, renders its prompt, asks, and stores the answer once.

    The run's brief and every earlier answer go into the prompt as blanks that the template
    declares untrusted, so each arrives inside an ``<untrusted>`` block: what a model wrote one
    stage ago is text from outside again, and a request that made it into the brief is data.

    **A stage gets only the tools its recipe names and the tools the tool lock grants it**, and none if
    there are none. The request offers
    those tools and the loop runs nothing else. A recipe that names a tool nobody registered stops
    the stage before anything is asked. Every stage goes through the tool loop, which for a stage
    with no tools is a single call.

    **A stage's prompt also carries the skills a person enabled for it**, as text added after the
    stage's own prompt, and the skills' identity is added to the prompt version so a resumed run
    replays an answer only for the same text. A skill is text and nothing more: it adds no tool,
    and it is not given a say in which tools are offered. A stage with no skill enabled sends
    exactly the prompt and version it always did.

    An answer that the stage after it could not read (the outline must parse as chapters) **stops the run
    where it was written**, before it is stored, so a malformed one is not paid for twice.

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
        loop: RunToolLoopInterface,
        tools: ToolRegistryInterface,
        grants: ToolGrantsInterface,
        guidance: StageGuidanceInterface,
        checks: StageOutputCheckInterface,
        guards: Callable[[Budget], SpendGuardInterface],
    ) -> None:
        self._recipes = recipes
        self._prompts = prompts
        self._artifacts = artifacts
        self._loop = loop
        self._tools = tools
        self._grants = grants
        self._guidance = guidance
        self._checks = checks
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
        prompt = self._render(template, "user", values)
        version = template.identifier()
        guidance = self._guidance.for_stage(run.stage)
        if not guidance.empty():
            prompt = f"{prompt}\n\n{guidance.text}"
            version = f"{version}+{guidance.identity}"
        request = ModelRequest(
            system=self._render(template, "system", values),
            prompt=prompt,
            max_output_tokens=recipe.max_output_tokens,
            prompt_version=version,
            tools=self._definitions(recipe, guidance.tools),
        )
        outcome = await asyncio.to_thread(
            self._loop.run, self._guards(run.budget), run.run_id, run.stage, attempt, request
        )
        if not outcome.complete or not outcome.text.strip():
            raise ApplicationError(
                code="STAGE_ANSWER_UNUSABLE", message=self._why(outcome, run.stage), http_status=502
            )
        self._checks.check(run.stage, outcome.text)
        await asyncio.to_thread(
            self._artifacts.put, run.run_id, recipe.output_name(), outcome.text.encode("utf-8")
        )
        return StageReport()

    def _recipe(self, stage: str) -> StageRecipe:
        try:
            return self._recipes.recipe(stage)
        except ValueError as error:
            raise ApplicationError(
                code="STAGE_HAS_NO_RECIPE", message=str(error), http_status=422
            ) from error

    def _offered(self, recipe: StageRecipe, extra: tuple[str, ...]) -> tuple[str, ...]:
        """The recipe's own tools, the locked-server tools the lock grants this stage, then the guidance's."""
        granted = tuple(
            name for name in self._grants.for_stage(recipe.stage) if name not in recipe.tools
        )
        own = recipe.tools + granted
        return own + tuple(name for name in extra if name not in own)

    def _definitions(
        self, recipe: StageRecipe, extra: tuple[str, ...]
    ) -> tuple[ToolDefinition, ...]:
        try:
            return self._tools.definitions(self._offered(recipe, extra))
        except ValueError as error:
            raise ApplicationError(
                code="STAGE_TOOL_UNKNOWN", message=str(error), http_status=500
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
    def _why(outcome: ToolLoopResult, stage: str) -> str:
        if outcome.issues:
            return f"{stage}: " + "; ".join(f"{i.code}: {i.detail}" for i in outcome.issues)
        return f"{stage}: the model returned no text"
