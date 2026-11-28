# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Revises one scene by asking the model through the same tool loop and spend guard every other stage uses."""

from collections.abc import Callable
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.prompt_library_interface import PromptLibraryInterface
from engineering_influence.interfaces.scene_reviser_interface import SceneReviserInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.prompt_template import PromptTemplate
from engineering_influence.models.scene_card import SceneCard
from engineering_influence.services.interfaces.run_tool_loop_interface import RunToolLoopInterface
from engineering_influence.services.interfaces.spend_guard_interface import SpendGuardInterface


class ModelSceneReviser(SceneReviserInterface):
    """The card and the drafted scene go into the prompt as untrusted blanks. An answer cut off at the model's limit,
    or empty, stops the stage; an answer that finished is returned for the stage to check, not judged here."""

    TEMPLATE: ClassVar[str] = "screenplay_revise_scene"
    MAX_OUTPUT_TOKENS: ClassVar[int] = 4_000
    STAGE_ATTEMPT: ClassVar[int] = 1

    def __init__(
        self,
        prompts: PromptLibraryInterface,
        loop: RunToolLoopInterface,
        guards: Callable[[Budget], SpendGuardInterface],
        template: str = TEMPLATE,
    ) -> None:
        """Remember the prompts, tool loop, spend guard and the prompt template for each revision."""
        self._prompts = prompts
        self._loop = loop
        self._guards = guards
        self._template = template

    def revise(self, run: BookRun, card: SceneCard, scene: str) -> str:
        """The revised scene, stripped, or ApplicationError when the model's answer is incomplete or empty."""
        template = self._prompts.get(self._template)
        values = {"card": card.body, "scene": scene}
        request = ModelRequest(
            system=self._render(template, "system", values),
            prompt=self._render(template, "user", values),
            max_output_tokens=self.MAX_OUTPUT_TOKENS,
            prompt_version=template.identifier(),
        )
        outcome = self._loop.run(
            self._guards(run.budget), run.run_id, run.stage, self.STAGE_ATTEMPT, request
        )
        if not outcome.complete or not outcome.text.strip():
            raise ApplicationError(
                code="STAGE_ANSWER_UNUSABLE",
                message=f"scene {card.number}: the model's revision is incomplete or empty",
                http_status=502,
            )
        return outcome.text.strip()

    @staticmethod
    def _render(template: PromptTemplate, part: str, values: dict[str, str]) -> str:
        text = template.parts.get(part, "")
        needed = set(template.BLANK.findall(text))
        return template.render(part, {name: values[name] for name in needed})
