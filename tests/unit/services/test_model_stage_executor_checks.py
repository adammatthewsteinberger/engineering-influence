# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""An answer a later stage could not read stops the run where it was written, before it is stored."""

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
from engineering_influence.models.quality_issue import QualityIssue
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


class Asker(AskModelInterface):
    def __init__(self, answer: ModelAnswer) -> None:
        self.answer = answer

    def ask(
        self,
        guard: SpendGuardInterface,
        run_id: str,
        stage: str,
        attempt: int,
        request: ModelRequest,
    ) -> ModelAnswer:
        return self.answer


class Checks(StageOutputCheckInterface):
    def __init__(self, fail: ApplicationError | None = None) -> None:
        self.fail = fail
        self.calls: list[tuple[str, str]] = []

    def check(self, stage: str, text: str, target_words: int | None) -> None:
        self.calls.append((stage, text))
        if self.fail:
            raise self.fail


def run_stage(stage: str, answer: ModelAnswer, checks: Checks) -> InMemoryArtifactStore:
    store = InMemoryArtifactStore()
    for name in NonfictionRecipes().recipe(stage).input_artifacts().values():
        store.put("run-1", name, b"earlier text")
    registry = ToolRegistry(())
    limits = ToolLoopLimits()
    executor = ModelStageExecutor(
        NonfictionRecipes(),
        TomlPromptLibrary(),
        store,
        RunToolLoop(Asker(answer), ToolRunner(registry, InMemoryJournal(), limits), limits),
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
        stage=stage,
    )
    asyncio.run(executor.execute(run, 1))
    return store


def complete(text: str) -> ModelAnswer:
    return ModelAnswer(text, True, (), 0, 1, False)


def test_a_usable_answer_is_checked_once_with_the_stage_and_its_text_and_then_stored() -> None:
    checks = Checks()
    store = run_stage("outline", complete("The outline."), checks)
    assert checks.calls == [("outline", "The outline.")]
    assert store.get("run-1", "outline.md") == b"The outline."


def test_an_answer_the_check_refuses_stops_the_stage_and_is_never_stored() -> None:
    refusal = ApplicationError(code="OUTLINE_INVALID", message="no chapters", http_status=422)
    checks = Checks(refusal)
    store = InMemoryArtifactStore()
    with pytest.raises(ApplicationError) as error:
        store = run_stage("outline", complete("Not an outline."), checks)
    assert (error.value.code, error.value.http_status) == ("OUTLINE_INVALID", 422)
    assert checks.calls == [("outline", "Not an outline.")]
    assert store.names("run-1") == []


def test_an_answer_that_is_not_complete_is_never_checked() -> None:
    issue = QualityIssue("outline", "model-cut-off", "cut off", blocking=True)
    checks = Checks()
    with pytest.raises(ApplicationError) as error:
        run_stage("outline", ModelAnswer("half an outline", False, (issue,), 0, 2, False), checks)
    assert error.value.code == "STAGE_ANSWER_UNUSABLE"
    assert checks.calls == []


def test_an_empty_answer_is_never_checked() -> None:
    checks = Checks()
    with pytest.raises(ApplicationError, match="no text"):
        run_stage("outline", complete("   "), checks)
    assert checks.calls == []


def test_every_stage_is_checked_and_the_check_decides_which_ones_matter() -> None:
    checks = Checks()
    run_stage("brief", complete("A brief."), checks)
    assert checks.calls == [("brief", "A brief.")]
