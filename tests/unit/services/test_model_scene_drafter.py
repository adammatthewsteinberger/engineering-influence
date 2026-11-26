# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ModelSceneDrafter: the scene's request carries its card as untrusted text, a retry asks again, and an unusable answer
stops the stage."""

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
from engineering_influence.models.scene_card import SceneCard
from engineering_influence.models.tool_loop_result import ToolLoopResult
from engineering_influence.services.model_scene_drafter import ModelSceneDrafter
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes


class Loop:
    """Answers with the given outcome and keeps every request it was asked to make."""

    def __init__(self, text: str, complete: bool = True) -> None:
        self.text = text
        self.complete = complete
        self.requests: list[ModelRequest] = []

    def run(
        self, guard, run_id: str, stage: str, attempt: int, request: ModelRequest
    ) -> ToolLoopResult:  # type: ignore[no-untyped-def]
        self.requests.append(request)
        issues = (
            () if self.complete else (QualityIssue("draft", "cut-off", "the answer was cut off"),)
        )
        return ToolLoopResult(
            text=self.text,
            complete=self.complete,
            issues=issues,
            cost_micro_usd=0,
            model_calls=1,
            tool_calls=0,
            turns=1,
            transcript=(),
        )


def run() -> BookRun:
    brief = BookBrief(BookKind.SCREENPLAY, "a bee colony in a dome", 5_000_000)
    return BookRun(
        run_id="run-1", brief=brief, plan=ScreenplayRecipes().plan(), budget=Budget(cap=5_000_000)
    )


CARD = SceneCard(
    2,
    "Set-Up",
    "## S02 · the hive\n**What changes:** the queen is found dead.\n**Beat:** Set-Up\n**Sources:** 001",
    (1,),
)


def drafter(loop: Loop) -> ModelSceneDrafter:
    return ModelSceneDrafter(TomlPromptLibrary(), loop, lambda budget: None)  # type: ignore[arg-type,return-value]


def test_the_scene_is_returned_stripped() -> None:
    loop = Loop("  INT. HIVE - DAY\n\nThe queen lies still.  \n")
    assert (
        drafter(loop).draft(run(), CARD, "anchors", "beats", "the sources", 1)
        == "INT. HIVE - DAY\n\nThe queen lies still."
    )


def test_the_card_is_sent_as_untrusted_text_and_the_system_part_names_no_blank() -> None:
    loop = Loop("INT. HIVE - DAY\n\nAction.")
    drafter(loop).draft(run(), CARD, "the anchors text", "the beats text", "the source text", 1)
    request = loop.requests[0]
    assert "<untrusted" in request.prompt
    assert "the queen is found dead" in request.prompt
    assert "the anchors text" in request.prompt and "the beats text" in request.prompt
    assert "the source text" in request.prompt
    assert "{{" not in request.system and "{{" not in request.prompt


def test_a_retry_has_its_own_prompt_version_so_the_failed_answer_is_not_replayed() -> None:
    loop = Loop("INT. HIVE - DAY\n\nAction.")
    drafter(loop).draft(run(), CARD, "a", "b", "s", 1)
    drafter(loop).draft(run(), CARD, "a", "b", "s", 2)
    first, second = loop.requests
    assert first.prompt_version.endswith("#try1")
    assert second.prompt_version.endswith("#try2")


def test_an_incomplete_answer_stops_the_stage() -> None:
    with pytest.raises(ApplicationError) as error:
        drafter(Loop("INT. HIVE", complete=False)).draft(run(), CARD, "a", "b", "s", 1)
    assert error.value.code == "STAGE_ANSWER_UNUSABLE"


def test_an_empty_answer_stops_the_stage() -> None:
    with pytest.raises(ApplicationError) as error:
        drafter(Loop("   ")).draft(run(), CARD, "a", "b", "s", 1)
    assert error.value.code == "STAGE_ANSWER_UNUSABLE"


def test_the_template_loads_from_the_shipped_library() -> None:
    template = TomlPromptLibrary().get("screenplay_draft_scene")
    assert template.identifier() == "screenplay_draft_scene@2"
