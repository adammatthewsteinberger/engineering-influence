# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ModelSourceDigester: the source goes in as untrusted text, and an unfinished or empty digest stops the stage."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.prompt_library.toml_prompt_library import (
    TomlPromptLibrary,
)
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.tool_loop_result import ToolLoopResult
from engineering_influence.services.model_source_digester import ModelSourceDigester
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes


class Loop:
    def __init__(self, text: str, complete: bool = True) -> None:
        self.text = text
        self.complete = complete
        self.requests: list[ModelRequest] = []

    def run(
        self, guard, run_id: str, stage: str, attempt: int, request: ModelRequest
    ) -> ToolLoopResult:  # type: ignore[no-untyped-def]
        self.requests.append(request)
        return ToolLoopResult(
            text=self.text,
            complete=self.complete,
            issues=()
            if self.complete
            else (QualityIssue("digest_sources", "cut-off", "the answer was cut off"),),
            cost_micro_usd=0,
            model_calls=1,
            tool_calls=0,
            turns=1,
            transcript=(),
        )


def run() -> BookRun:
    brief = BookBrief(BookKind.SCREENPLAY, "a film", 5_000_000)
    return BookRun(
        run_id="run-1", brief=brief, plan=ScreenplayRecipes().plan(), budget=Budget(cap=5_000_000)
    )


def digester(loop: Loop) -> ModelSourceDigester:
    return ModelSourceDigester(TomlPromptLibrary(), loop, lambda budget: None)  # type: ignore[arg-type,return-value]


def test_the_digest_is_the_models_answer_stripped() -> None:
    assert (
        digester(Loop("  Sol 240 was a Saturday.  \n")).digest(run(), "the source")
        == "Sol 240 was a Saturday."
    )


def test_the_source_goes_into_the_prompt_as_untrusted_text() -> None:
    loop = Loop("ok")
    digester(loop).digest(run(), "Sol 240: the card arrived.")
    assert "Sol 240: the card arrived." in loop.requests[0].prompt
    assert "untrusted" in loop.requests[0].system


def test_an_unfinished_digest_stops_the_stage() -> None:
    with pytest.raises(ApplicationError) as error:
        digester(Loop("half a sen", complete=False)).digest(run(), "the source")
    assert error.value.code == "STAGE_ANSWER_UNUSABLE"


def test_an_empty_digest_stops_the_stage() -> None:
    with pytest.raises(ApplicationError) as error:
        digester(Loop("   ")).digest(run(), "the source")
    assert error.value.code == "STAGE_ANSWER_UNUSABLE"
