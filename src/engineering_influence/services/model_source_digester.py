# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Condenses one source file by asking the model through the same tool loop and spend guard every other stage uses."""

from collections.abc import Callable
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.prompt_library_interface import PromptLibraryInterface
from engineering_influence.interfaces.source_digester_interface import SourceDigesterInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.prompt_template import PromptTemplate
from engineering_influence.services.interfaces.run_tool_loop_interface import RunToolLoopInterface
from engineering_influence.services.interfaces.spend_guard_interface import SpendGuardInterface


class ModelSourceDigester(SourceDigesterInterface):
    """The source goes into the prompt as an untrusted blank. An answer cut off at the model's limit, or empty, stops
    the stage: a digest that stops mid-sentence would hide what the source says."""

    TEMPLATE: ClassVar[str] = "screenplay_digest_source"
    MAX_OUTPUT_TOKENS: ClassVar[int] = 4_000
    STAGE_ATTEMPT: ClassVar[int] = 1

    def __init__(
        self,
        prompts: PromptLibraryInterface,
        loop: RunToolLoopInterface,
        guards: Callable[[Budget], SpendGuardInterface],
    ) -> None:
        self._prompts = prompts
        self._loop = loop
        self._guards = guards

    def digest(self, run: BookRun, source: str) -> str:
        """The condensed source, stripped, or ApplicationError when the model's answer is incomplete or empty."""
        template = self._prompts.get(self.TEMPLATE)
        values = {"source": source}
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
                message="a source's digest is incomplete or empty; the model stopped before it finished",
                http_status=502,
            )
        return outcome.text.strip()

    @staticmethod
    def _render(template: PromptTemplate, part: str, values: dict[str, str]) -> str:
        text = template.parts.get(part, "")
        needed = set(template.BLANK.findall(text))
        return template.render(part, {name: values[name] for name in needed})
