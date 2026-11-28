# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""A stage whose check is repairable gets one more call, with the findings in its prompt; a repair that fails too stops the
stage with the code the check names."""

import asyncio

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.in_memory_journal import InMemoryJournal
from engineering_influence.infrastructure.prompt_library.toml_prompt_library import (
    TomlPromptLibrary,
)
from engineering_influence.interfaces.stage_output_check_interface import (
    StageOutputCheckInterface,
)
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.model_answer import ModelAnswer
from engineering_influence.models.model_request import ModelRequest
from engineering_influence.models.tool_lock import ToolLock
from engineering_influence.models.tool_loop_limits import ToolLoopLimits
from engineering_influence.services.interfaces.ask_model_interface import AskModelInterface
from engineering_influence.services.interfaces.spend_guard_interface import SpendGuardInterface
from engineering_influence.services.lock_tool_grants import LockToolGrants
from engineering_influence.services.model_stage_executor import ModelStageExecutor
from engineering_influence.services.no_stage_guidance import NoStageGuidance
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.run_tool_loop import RunToolLoop
from engineering_influence.services.spend_guard import SpendGuard
from engineering_influence.services.tool_registry import ToolRegistry
from engineering_influence.services.tool_runner import ToolRunner

CAP = 5_000_000


class Sequence(AskModelInterface):
    """Answers each call with the next scripted text, and keeps every request it was sent."""

    def __init__(self, *texts: str) -> None:
        self.texts = list(texts)
        self.requests: list[ModelRequest] = []

    def ask(
        self,
        guard: SpendGuardInterface,
        run_id: str,
        stage: str,
        attempt: int,
        request: ModelRequest,
    ) -> ModelAnswer:
        self.requests.append(request)
        return ModelAnswer(self.texts.pop(0), True, (), 0, 1, False)


class Checks(StageOutputCheckInterface):
    """Refuses any answer that says BAD, with a named problem; a stage is repairable and its repair code is FINAL."""

    FINAL = "SCREENPLAY_OUTLINE_INVALID"

    def __init__(self, repairable: bool = True) -> None:
        self._repairable = repairable

    def check(self, stage: str, text: str, target_words: int | None) -> None:
        if "BAD" in text:
            raise ApplicationError(
                code="STAGE_OUTPUT_INVALID",
                message=f"{stage}: the beat sheet is missing a beat",
                http_status=422,
            )

    def repairable(self, stage: str) -> bool:
        return self._repairable

    def final_code(self, stage: str) -> str:
        return self.FINAL


def run_stage(asker: Sequence, checks: Checks) -> InMemoryArtifactStore:
    store = InMemoryArtifactStore()
    for name in NonfictionRecipes().recipe("outline").input_artifacts().values():
        store.put("run-1", name, b"earlier text")
    registry = ToolRegistry(())
    limits = ToolLoopLimits()
    executor = ModelStageExecutor(
        NonfictionRecipes(),
        TomlPromptLibrary(),
        store,
        RunToolLoop(asker, ToolRunner(registry, InMemoryJournal(), limits), limits),
        registry,
        LockToolGrants(ToolLock()),
        NoStageGuidance(),
        checks,
        lambda budget: SpendGuard(budget),
    )
    run = BookRun(
        "run-1",
        BookBrief(BookKind.NONFICTION, "How to keep bees", CAP),
        NonfictionRecipes().plan(),
        Budget(cap=CAP),
        stage="outline",
    )
    asyncio.run(executor.execute(run, 1))
    return store


def test_a_failing_answer_gets_one_repair_call_that_names_the_findings_and_the_repair_is_stored() -> (
    None
):
    asker = Sequence("BAD first draft", "a good outline")
    store = run_stage(asker, Checks())
    assert len(asker.requests) == 2
    assert "the beat sheet is missing a beat" in asker.requests[1].prompt
    assert store.get("run-1", "outline.md") == b"a good outline"


def test_a_repair_that_also_fails_stops_with_the_code_the_check_names_and_stores_nothing() -> None:
    asker = Sequence("BAD first draft", "BAD again")
    with pytest.raises(ApplicationError) as error:
        run_stage(asker, Checks())
    assert error.value.code == Checks.FINAL
    assert "the beat sheet is missing a beat" in error.value.message
    assert len(asker.requests) == 2


def test_a_stage_that_is_not_repairable_is_asked_once_and_keeps_the_generic_code() -> None:
    asker = Sequence("BAD first draft", "never asked")
    with pytest.raises(ApplicationError) as error:
        run_stage(asker, Checks(repairable=False))
    assert error.value.code == "STAGE_OUTPUT_INVALID"
    assert len(asker.requests) == 1


class OtherFailure(Checks):
    """Passes the first answer's check, then refuses the repair with a code that is not the output check's."""

    def check(self, stage: str, text: str, target_words: int | None) -> None:
        if "fixed" in text:
            raise ApplicationError(
                code="OUTLINE_CHAPTERS_WRONG", message="wrong count", http_status=422
            )
        super().check(stage, text, target_words)


def test_a_repair_refused_with_some_other_code_keeps_that_code() -> None:
    asker = Sequence("BAD first draft", "fixed but still wrong")
    with pytest.raises(ApplicationError) as error:
        run_stage(asker, OtherFailure())
    assert error.value.code == "OUTLINE_CHAPTERS_WRONG"
    assert len(asker.requests) == 2
